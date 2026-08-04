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
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

import {
  GlobalRefreshControl,
  seedRefreshIntervalSeconds,
  useGlobalRefresh
} from '../GlobalRefreshControl'
import { rollingRange, useGlobalTimeRange } from '../GlobalTimePicker'
import { type CustomGraphObject, getCustomGraph } from './api'
import DesignerBody from './components/DesignerBody.vue'
import DesignerHeader from './components/DesignerHeader.vue'
import type { SelectableGraph } from './components/GraphSelector.vue'
import { pushUrlState, replaceUrlState } from './urlState'

const props = defineProps<CustomGraphDesigner>()

// Single owner of the shared time-range default; header and body only read/update it.
const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()
if (activeTimeRange.value === null) {
  setActiveTimeRange(rollingRange(props.time_picker.default_time_range))
}

seedRefreshIntervalSeconds(props.time_picker.default_refresh_time)

const current = ref<{ name: string; owner: string }>({
  name: props.graph_name,
  owner: props.graph_owner
})
const graph = shallowRef<CustomGraphObject | null>(null)
const etag = ref<string | null>(null)
const mode = ref<CustomGraphDesignerMode>('view')
const isLoading = ref(false)
const loadError = ref<string | null>(null)
const loadCounter = ref(0)

const { loadFilterDefinitions } = useProvideFilterDefinitions()
const filtersReady = ref(false)
const filtersError = ref<string | null>(null)
const displaySettings = ref<boolean>(false)

const ownerParam = computed(() =>
  current.value.owner === props.logged_in_user ? undefined : current.value.owner
)

const isEditable = computed(() => graph.value?.extensions.is_editable === true)

const selectedGraph = computed<SelectableGraph | null>(() =>
  graph.value === null
    ? null
    : {
        name: current.value.name,
        owner: current.value.owner,
        title: graph.value.title ?? current.value.name
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

const bodyRef = ref<InstanceType<typeof DesignerBody> | null>(null)

function urlState(): { name: string; owner: string; mode: CustomGraphDesignerMode } {
  return { name: current.value.name, owner: current.value.owner, mode: mode.value }
}

// Guards against a slow response arriving after a newer load was issued.
let loadToken = 0

async function load(requestedMode: CustomGraphDesignerMode): Promise<void> {
  const token = ++loadToken
  isLoading.value = true
  loadError.value = null
  try {
    const result = await getCustomGraph(current.value.name, ownerParam.value)
    if (token !== loadToken) {
      return
    }
    graph.value = result.graph
    etag.value = result.etag
    mode.value = requestedMode === 'edit' && result.graph.extensions.is_editable ? 'edit' : 'view'
    replaceUrlState(urlState())
  } catch (e) {
    if (token !== loadToken) {
      return
    }
    graph.value = null
    loadError.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (token === loadToken) {
      isLoading.value = false
    }
  }
}

const { setRefreshPaused } = useGlobalRefresh()
const onPopState = (): void => window.location.reload()

onMounted(() => {
  setRefreshPaused(false)
  window.addEventListener('popstate', onPopState)
  void loadFilterDefinitions()
    .then(() => {
      filtersReady.value = true
    })
    .catch((e: unknown) => {
      filtersError.value = e instanceof Error ? e.message : String(e)
    })
  void load(props.mode)
})

onBeforeUnmount(() => {
  window.removeEventListener('popstate', onPopState)
})

function onGraphChange(selected: SelectableGraph): void {
  current.value = { name: selected.name, owner: selected.owner }
  mode.value = 'view'
  loadCounter.value += 1
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
  // Remounting the body re-seeds its items from the last loaded graph.
  loadCounter.value += 1
  mode.value = 'view'
  replaceUrlState(urlState())
}

function onSaved(savedGraph: CustomGraphObject, savedEtag: string | null): void {
  graph.value = savedGraph
  etag.value = savedEtag
  mode.value = 'view'
  replaceUrlState(urlState())
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
        @enter-edit="onEnterEdit"
        @save="bodyRef?.save()"
        @cancel-edit="onCancelEdit"
        @graph-change="onGraphChange"
        @enter-settings="() => (displaySettings = true)"
      />
    </header>

    <div class="graphing-custom-graph-designer-app__content">
      <CmkAlertBox v-if="loadError !== null || filtersError !== null" variant="error">
        {{ loadError ?? filtersError }}
      </CmkAlertBox>
      <CmkIcon
        v-else-if="isLoading || graph === null || !filtersReady"
        name="load-graph"
        size="xxlarge"
      />
      <DesignerBody
        v-else
        :key="`${current.owner}/${current.name}/${loadCounter}`"
        ref="bodyRef"
        v-model:display-settings="displaySettings"
        :graph="graph"
        :graph-name="current.name"
        :etag="etag"
        :owner-param="ownerParam"
        :mode="mode"
        :palette="palette"
        :thresholds="{ warning: warning_color, critical: critical_color }"
        :metric-backend-available="metric_backend_available"
        :title-macros="title_macros"
        @saved="onSaved"
      />
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
  z-index: 1;
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
