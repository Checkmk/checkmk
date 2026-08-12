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
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

import {
  GlobalRefreshControl,
  seedRefreshIntervalSeconds,
  useGlobalRefresh
} from '../GlobalRefreshControl'
import { rollingRange, useGlobalTimeRange } from '../GlobalTimePicker'
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
import { useGraphItems } from './composables/useGraphItems'
import { fromApiDataSource, toApiDataSources } from './drafts'
import type { ItemId } from './types'
import { pushUrlState, replaceUrlState } from './urlState'

const props = defineProps<CustomGraphDesigner>()
const { _t } = usei18n()

// Single owner of the shared time-range default; header and body only read/update it.
const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()
if (activeTimeRange.value === null) {
  setActiveTimeRange(rollingRange(props.time_picker.default_time_range), 'time_picker')
}

seedRefreshIntervalSeconds(props.time_picker.default_refresh_time)

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

const { loadFilterDefinitions } = useProvideFilterDefinitions()
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

const saveError = ref<string | null>(null)
const isSaving = ref(false)

function resetEditor(graph: CustomGraphObject): void {
  store.replaceAll(graph.extensions.content.data_sources.map(fromApiDataSource))
  graphOptions.value = graph.extensions.content.graph_options
  saveError.value = null
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

const { setRefreshPaused } = useGlobalRefresh()
const onPopState = (): void => window.location.reload()

onMounted(() => {
  setRefreshPaused(false)
  window.addEventListener('popstate', onPopState)
  loadFilters()
  void load(props.mode)
})

onBeforeUnmount(() => {
  window.removeEventListener('popstate', onPopState)
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

/** Rows the wire format cannot express: incomplete drafts and formulas with broken refs. */
function invalidRowIds(): ItemId[] {
  const keptIds = new Set(toApiDataSources(store.items.value).map((source) => source.id))
  return store.items.value.map((item) => item.id).filter((id) => !keptIds.has(id))
}

async function save(): Promise<void> {
  const edited = loaded.value
  const editedOptions = graphOptions.value
  if (isSaving.value || edited === null || editedOptions === null) {
    return
  }
  const invalid = invalidRowIds()
  if (invalid.length > 0) {
    saveError.value = _t(
      'These rows are incomplete or reference incomplete rows and cannot be saved: %{ids}',
      { ids: invalid.join(', ') }
    )
    return
  }
  saveError.value = null
  isSaving.value = true
  try {
    const result = await updateCustomGraph(
      current.value.name,
      edited.etag,
      {
        title: edited.graph.title ?? current.value.name,
        metadata: edited.graph.extensions.metadata,
        content: {
          graph_options: editedOptions,
          data_sources: toApiDataSources(store.items.value)
        }
      },
      ownerParam.value
    )
    loaded.value = result
    mode.value = 'view'
    replaceUrlState(urlState())
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e)
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="graphing-custom-graph-designer-app">
    <header class="graphing-custom-graph-designer-app__header">
      <div class="graphing-custom-graph-designer-app__topbar">
        <CmkBreadcrumb
          class="graphing-custom-graph-designer-app__breadcrumb"
          :items="activeBreadcrumb"
        />
        <GlobalRefreshControl class="graphing-custom-graph-designer-app__refresh" />
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
        @update-graph-options="graphOptions = $event"
      >
        <template #alerts>
          <CmkAlertBox v-if="mode === 'edit' && saveError !== null" variant="error">
            {{ saveError }}
          </CmkAlertBox>
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
  border-bottom: 1px solid var(--ux-theme-4);
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
</style>
