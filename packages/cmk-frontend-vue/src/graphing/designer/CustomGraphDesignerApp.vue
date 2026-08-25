<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  CustomGraphDesigner,
  CustomGraphDesignerMode
} from 'cmk-shared-typing/typescript/custom_graph_designer'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkBreadcrumb, { type BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

import { GlobalRefreshControl } from '../GlobalRefreshControl'
import { initGlobalRefresh, rollingRange, useGlobalTimeRange } from '../GlobalTimePicker'
import {
  type CustomGraphObject,
  type CustomGraphOptions,
  type LoadedCustomGraph,
  getCustomGraph,
  updateCustomGraph
} from './api'
import DesignerBody from './components/DesignerBody.vue'
import DesignerHeader from './components/DesignerHeader.vue'
import type { SelectableGraph } from './components/GraphSelector.vue'
import { type SaveAction, type SaveFailure, useSaveFailures } from './composables/saveFailure'
import { useGraphItems } from './composables/useGraphItems'
import { fromApiDataSource, toApiDataSources } from './drafts'
import type { GraphItem, ItemId } from './types'
import { pushUrlState, replaceUrlState } from './urlState'
import { type RowIssue, isValid, validateDesign } from './validation'

const ANY_VERSION = '*'

const props = defineProps<CustomGraphDesigner>()
const { _t, _tn } = usei18n()
const { describeSaveFailure } = useSaveFailures()

// Single owner of the shared time-range default; header and body only read/update it.
const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()
if (activeTimeRange.value === null) {
  setActiveTimeRange(rollingRange(props.time_picker.default_time_range), 'time_picker')
}

initGlobalRefresh({ intervalSeconds: props.time_picker.refresh.interval_seconds, live: true })

function returnToLiveMonitoring(): void {
  setActiveTimeRange(rollingRange(props.time_picker.default_time_range), 'time_picker')
}

const current = ref<{ name: string; owner: string }>({
  name: props.graph_name,
  owner: props.graph_owner
})
const loaded = shallowRef<LoadedCustomGraph | null>(null)
const mode = ref<CustomGraphDesignerMode>('view')
const isLoading = ref(false)
const loadError = ref<string | null>(null)

const store = useGraphItems(props.palette)
const graphOptions = ref<CustomGraphOptions | null>(null)

const { filterDefinitions, loadFilterDefinitions } = useProvideFilterDefinitions()
const filtersReady = ref(false)
const filtersError = ref<string | null>(null)
const displaySettings = ref<boolean>(false)

const ownerParam = computed(() =>
  current.value.owner === props.logged_in_user ? undefined : current.value.owner
)

const isEditable = computed(() => loaded.value?.graph.extensions.is_editable === true)

const selectedGraph = computed<SelectableGraph | null>(() =>
  loaded.value === null
    ? null
    : {
        name: current.value.name,
        owner: current.value.owner,
        title: loaded.value.graph.title ?? current.value.name
      }
)

// The backend ships the "Customize > Custom graphs" prefix; append the loaded graph's title.
const activeBreadcrumb = computed<BreadcrumbItem[]>(() =>
  selectedGraph.value === null
    ? props.initial_breadcrumb
    : [...props.initial_breadcrumb, { title: selectedGraph.value.title, link: null }]
)

watch(selectedGraph, (selected) => {
  if (selected !== null) {
    document.title = selected.title
  }
})

const saveFailure = ref<SaveFailure | null>(null)
const isSaving = ref(false)
/** Until a save has been tried, an unfinished source is work in progress, not an error. */
const hasAttemptedSave = ref(false)
const issuesAlert = ref<HTMLElement | null>(null)

const blockingIssues = computed(() => validateDesign(store.items.value, filterDefinitions.value))

const issuesByRow = computed(() => {
  const byRow = new Map<ItemId, RowIssue[]>()
  if (!hasAttemptedSave.value) {
    return byRow
  }
  for (const issue of blockingIssues.value) {
    byRow.set(issue.id, [...(byRow.get(issue.id) ?? []), issue])
  }
  return byRow
})

const showsSaveIssues = computed(() => hasAttemptedSave.value && blockingIssues.value.length > 0)
const showsAlerts = computed(() => showsSaveIssues.value || saveFailure.value !== null)

const blockedIds = computed(() => {
  const blocked = new Set(blockingIssues.value.map((issue) => issue.id))
  return store.items.value.filter((item) => blocked.has(item.id)).map((item) => item.id)
})

const blockedSummary = computed(() =>
  _tn(
    'Fix the issues with ID %{ids}, then try saving again.',
    'Fix the issues with IDs %{ids}, then try saving again.',
    blockedIds.value.length,
    { ids: blockedIds.value.join(', ') }
  )
)

function snapshot(): string {
  return JSON.stringify({ items: store.items.value, options: graphOptions.value })
}

const committedSnapshot = ref<string | null>(null)

const isDirty = computed(
  () =>
    mode.value === 'edit' &&
    committedSnapshot.value !== null &&
    snapshot() !== committedSnapshot.value
)

function warnBeforeUnload(event: BeforeUnloadEvent): void {
  event.preventDefault()
  event.returnValue = ''
}

watch(isDirty, (dirty) => {
  if (dirty) {
    window.addEventListener('beforeunload', warnBeforeUnload)
  } else {
    window.removeEventListener('beforeunload', warnBeforeUnload)
  }
})

function resetEditor(graph: CustomGraphObject): void {
  store.replaceAll(graph.extensions.content.data_sources.map(fromApiDataSource))
  graphOptions.value = graph.extensions.content.graph_options
  hasAttemptedSave.value = false
  saveFailure.value = null
  committedSnapshot.value = snapshot()
}

function urlState(): { name: string; owner: string; mode: CustomGraphDesignerMode } {
  return { name: current.value.name, owner: current.value.owner, mode: mode.value }
}

// Guards against a slow response arriving after a newer load was issued.
let loadToken = 0

// `mode` below only advances once a load has succeeded, so a retry reads this instead: otherwise a
// failed first load leaves it at its default and drops what an `?mode=edit` deep link asked for.
let lastRequestedMode: CustomGraphDesignerMode = props.mode

async function load(requestedMode: CustomGraphDesignerMode): Promise<void> {
  const token = ++loadToken
  lastRequestedMode = requestedMode
  isLoading.value = true
  loadError.value = null
  try {
    const result = await getCustomGraph(current.value.name, ownerParam.value)
    if (token !== loadToken) {
      return
    }
    loaded.value = result
    resetEditor(result.graph)
    mode.value = requestedMode === 'edit' && result.graph.extensions.is_editable ? 'edit' : 'view'
    replaceUrlState(urlState())
  } catch (e) {
    if (token !== loadToken) {
      return
    }
    loaded.value = null
    loadError.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (token === loadToken) {
      isLoading.value = false
    }
  }
}

function loadFilters(): void {
  filtersError.value = null
  void loadFilterDefinitions()
    .then(() => {
      filtersReady.value = true
    })
    .catch((e: unknown) => {
      filtersError.value = e instanceof Error ? e.message : String(e)
    })
}

// The graph and the filter definitions load independently and the box states whichever failed, so
// retry re-runs the one that did; otherwise a filter error would stand with nothing refreshing it.
function onRetry(): void {
  if (filtersError.value !== null) {
    loadFilters()
  }
  if (loadError.value !== null) {
    void load(lastRequestedMode)
  }
}

const onPopState = (): void => window.location.reload()

onMounted(() => {
  window.addEventListener('popstate', onPopState)
  loadFilters()
  void load(props.mode)
})

onBeforeUnmount(() => {
  window.removeEventListener('popstate', onPopState)
  window.removeEventListener('beforeunload', warnBeforeUnload)
})

function onGraphChange(selected: SelectableGraph): void {
  current.value = { name: selected.name, owner: selected.owner }
  mode.value = 'view'
  pushUrlState(urlState())
  void load('view')
}

function onEnterEdit(): void {
  if (isEditable.value) {
    mode.value = 'edit'
    replaceUrlState(urlState())
  }
}

function onCancelEdit(): void {
  if (loaded.value !== null) {
    resetEditor(loaded.value.graph)
  }
  mode.value = 'view'
  replaceUrlState(urlState())
}

// The alert box carries role="alert", so its first appearance is announced on its own; a repeat
// attempt leaves the DOM unchanged, with nothing to announce, and moves focus there instead.
function revealBlockingIssues(announceByFocus: boolean): void {
  issuesAlert.value?.scrollIntoView({ block: 'nearest' })
  if (announceByFocus) {
    issuesAlert.value?.focus({ preventScroll: true })
  }
}

async function save(): Promise<void> {
  await saveAgainst('loaded')
}

async function overwrite(): Promise<void> {
  await saveAgainst('any')
}

async function saveAgainst(version: 'loaded' | 'any'): Promise<void> {
  const edited = loaded.value
  const editedOptions = graphOptions.value
  if (isSaving.value || edited === null || editedOptions === null) {
    return
  }
  const wasBlocked = showsSaveIssues.value
  saveFailure.value = null
  hasAttemptedSave.value = true
  if (blockingIssues.value.length > 0) {
    void nextTick(() => revealBlockingIssues(wasBlocked))
    return
  }
  const ifMatch = version === 'any' ? ANY_VERSION : edited.etag
  isSaving.value = true
  try {
    const result = await updateCustomGraph(
      current.value.name,
      ifMatch,
      {
        title: edited.graph.title ?? current.value.name,
        metadata: edited.graph.extensions.metadata,
        content: {
          graph_options: editedOptions,
          data_sources: toApiDataSources(
            store.items.value.filter((item): item is GraphItem =>
              isValid(item, filterDefinitions.value)
            )
          )
        }
      },
      ownerParam.value
    )
    hasAttemptedSave.value = false
    loaded.value = result
    committedSnapshot.value = snapshot()
    mode.value = 'view'
    replaceUrlState(urlState())
  } catch (e) {
    saveFailure.value = describeSaveFailure(e)
  } finally {
    isSaving.value = false
  }
}

function saveActionButton(action: SaveAction): { title: TranslatedString; onclick: () => void } {
  switch (action) {
    case 'retry':
      return { title: _t('Retry'), onclick: () => void save() }
    case 'reload':
      return { title: _t('Reload'), onclick: () => window.location.reload() }
    case 'overwrite':
      return { title: _t('Overwrite'), onclick: () => void overwrite() }
  }
}

// exactOptionalPropertyTypes rejects an explicit undefined, so a failure with fewer actions than
// the alert has buttons has to omit the keys rather than pass one.
const saveFailureButtons = computed(() => {
  const [main, optional] = saveFailure.value?.actions ?? []
  if (main === undefined) {
    return {}
  }
  if (optional === undefined) {
    return { mainButton: saveActionButton(main) }
  }
  return { mainButton: saveActionButton(main), optionalButton: saveActionButton(optional) }
})
</script>

<template>
  <div class="graphing-custom-graph-designer-app">
    <header class="graphing-custom-graph-designer-app__header">
      <div class="graphing-custom-graph-designer-app__topbar">
        <CmkBreadcrumb
          class="graphing-custom-graph-designer-app__breadcrumb"
          :items="activeBreadcrumb"
        />
        <GlobalRefreshControl
          class="graphing-custom-graph-designer-app__refresh"
          @resume="returnToLiveMonitoring"
        />
      </div>

      <DesignerHeader
        :selected="selectedGraph"
        :logged-in-user="logged_in_user"
        :mode="mode"
        :is-editable="isEditable"
        :time-picker="time_picker"
        :saving="isSaving"
        @enter-edit="onEnterEdit"
        @save="void save()"
        @cancel-edit="onCancelEdit"
        @graph-change="onGraphChange"
        @enter-settings="() => (displaySettings = true)"
      />
    </header>

    <div class="graphing-custom-graph-designer-app__content">
      <CmkAlertBox
        v-if="loadError !== null || filtersError !== null"
        variant="error"
        :main-button="{ title: _t('Retry'), onclick: onRetry }"
      >
        {{ loadError ?? filtersError }}
      </CmkAlertBox>
      <CmkIcon
        v-else-if="isLoading || loaded === null || graphOptions === null || !filtersReady"
        name="load-graph"
        size="xxlarge"
      />
      <DesignerBody
        v-else
        :key="`${current.owner}/${current.name}`"
        v-model:display-settings="displaySettings"
        :store="store"
        :graph-options="graphOptions"
        :title="loaded.graph.title ?? current.name"
        :mode="mode"
        :thresholds="{ warning: warning_color, critical: critical_color }"
        :metric-backend-available="metric_backend_available"
        :create-services-available="create_services_available"
        :metric-backend-default-title="metric_backend_default_title"
        :title-macros="title_macros"
        :issues-by-row="issuesByRow"
        @update-graph-options="graphOptions = $event"
      >
        <template #alerts>
          <div v-if="mode === 'edit' && showsAlerts" ref="issuesAlert" tabindex="-1">
            <CmkAlertBox
              v-if="showsSaveIssues"
              class="graphing-custom-graph-designer-app__issues-alert"
              variant="error"
            >
              {{ blockedSummary }}
            </CmkAlertBox>
            <CmkAlertBox
              v-if="saveFailure !== null"
              variant="error"
              :heading="saveFailure.detail !== null ? saveFailure.message : undefined"
              v-bind="saveFailureButtons"
            >
              {{ saveFailure.detail ?? saveFailure.message }}
            </CmkAlertBox>
          </div>
        </template>
      </DesignerBody>
    </div>
  </div>
</template>

<style scoped>
.graphing-custom-graph-designer-app {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: var(--ux-theme-1);

  --graphing-custom-graph-designer-app-header-stroke: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .graphing-custom-graph-designer-app {
  --graphing-custom-graph-designer-app-header-stroke: var(--color-mid-grey-100);
}

.graphing-custom-graph-designer-app__header {
  position: sticky;
  top: 0;

  /* Above the sticky header and footer rows of the tables below, which carry z-indices of their
     own. Kept well under the overlay scale so floating content still opens over the header. */
  z-index: 10;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: var(--dimension-6);
  padding-bottom: 0;
  background: var(--ux-theme-2);
  border-bottom: 1px solid var(--graphing-custom-graph-designer-app-header-stroke);
}

.graphing-custom-graph-designer-app__topbar {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-6);
}

.graphing-custom-graph-designer-app__breadcrumb {
  flex: 1 1 auto;
  min-width: 0;
}

.graphing-custom-graph-designer-app__refresh {
  flex: 0 0 auto;
  height: 0;
  overflow: visible;
  position: relative;
  z-index: 1;
}

.graphing-custom-graph-designer-app__content {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 0;
  overflow: auto;
}

.graphing-custom-graph-designer-app__content > * {
  margin: var(--dimension-6);
}

.graphing-custom-graph-designer-app__issues-alert {
  align-items: center;
}
</style>
