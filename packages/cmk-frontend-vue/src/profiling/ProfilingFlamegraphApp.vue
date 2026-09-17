<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkCollapsible from 'cmk-ui-library/components/CmkCollapsible/CmkCollapsible.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import { cmkFetch } from 'cmk-ui-library/lib/cmkFetch'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { computed, onMounted, ref, watch } from 'vue'

import FlamegraphCanvas from './components/FlamegraphCanvas.vue'
import HotspotsTable from './components/HotspotsTable.vue'
import type {
  CallerInfo,
  FlamegraphNode,
  HotspotData,
  ProfileSourceType,
  ProfilingFlamegraphData
} from './types'
import { formatCount, formatMs, formatTimestamp } from './utils/format'

const props = defineProps<{
  profile_id: string
  data_url: string
}>()

const { _t } = usei18n()

function sourceLabel(source: ProfileSourceType): string {
  switch (source) {
    case 'gui_request':
      return _t('GUI request')
    case 'file_upload':
      return _t('Upload')
    case 'base_command':
      return _t('cmk --profile')
  }
}

const payload = ref<ProfilingFlamegraphData | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const res = await cmkFetch(props.data_url, { credentials: 'same-origin' })
    await res.raiseForStatus()
    payload.value = (await res.json()) as ProfilingFlamegraphData
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

const metadata = computed(() => payload.value?.metadata ?? null)
const hotspots = computed<HotspotData[]>(() => payload.value?.hotspots ?? [])
const flamegraphTree = computed<FlamegraphNode | null>(() => payload.value?.flamegraph_tree ?? null)
const totalTime = computed(() => payload.value?.total_time ?? 0)
const totalCalls = computed(() => payload.value?.total_calls ?? 0)
const totalFunctions = computed(() => payload.value?.total_functions ?? 0)

const graphSearchQuery = ref('')
const tableSearchQuery = ref('')
const graphSearchValue = ref('')
const tableSearchValue = ref('')
const highlightFunction = ref('')
// Zoom history: each entry is the root function the user zoomed into.
// Clicking a child frame pushes; clicking the topmost frame pops.
const zoomStack = ref<string[]>([])
const headerExpanded = ref(false)

const zoomedRoot = computed(() =>
  zoomStack.value.length > 0 ? zoomStack.value[zoomStack.value.length - 1]! : ''
)

function onGraphSelectFunction(name: string) {
  highlightFunction.value = name
  if (name && name !== zoomedRoot.value) {
    zoomStack.value.push(name)
  }
}

function onGraphZoomOut() {
  if (zoomStack.value.length > 0) {
    zoomStack.value.pop()
  }
  highlightFunction.value = zoomedRoot.value
}

// A hotspots-table row (or one of its caller/callee entries) navigates the
// flamegraph to that function: the graph re-roots to it exactly as clicking its
// frame would. This reaches functions that are not part of the currently shown
// stack — the subtree is rebuilt from the picked function's own callees.
function onTableSelectFunction(name: string) {
  onGraphSelectFunction(name)
}

const syncGraphQuery = useDebounceFn((value: string) => {
  graphSearchQuery.value = value
}, 120)

const syncTableQuery = useDebounceFn((value: string) => {
  tableSearchQuery.value = value
}, 120)

watch(graphSearchValue, (v) => syncGraphQuery(v))
watch(tableSearchValue, (v) => syncTableQuery(v))

function clearGraphSearch() {
  graphSearchValue.value = ''
  graphSearchQuery.value = ''
}

function clearTableSearch() {
  tableSearchValue.value = ''
  tableSearchQuery.value = ''
}

const hotspotsByFunction = computed(() => {
  const map = new Map<string, HotspotData>()
  for (const h of hotspots.value) {
    map.set(h.function, h)
  }
  return map
})

const callersByFunction = computed(() => {
  const map = new Map<string, CallerInfo[]>()
  for (const h of hotspots.value) {
    map.set(h.function, h.top_callers)
  }
  return map
})

const functionPaths = computed<Record<string, string>>(() => payload.value?.function_paths ?? {})

function buildDynamicTree(rootName: string): FlamegraphNode {
  // Global expanded set — each function is expanded (children recursed into) only
  // once. Subsequent occurrences appear as leaves. Keeps tree size linear in the
  // number of unique functions, avoiding exponential blowup on interconnected graphs.
  const expanded = new Set<string>()
  const maxDepth = 20

  function build(name: string, depth: number): FlamegraphNode {
    const hotspot = hotspotsByFunction.value.get(name)
    const selfTime = hotspot ? hotspot.self_time_ms / 1000 : 0
    const cumTime = hotspot ? hotspot.cumulative_time_ms / 1000 : 0
    const callees = hotspot?.top_callees ?? []

    const children: FlamegraphNode[] = []
    if (depth < maxDepth && !expanded.has(name)) {
      expanded.add(name)
      for (const callee of callees) {
        children.push(build(callee.function, depth + 1))
      }
    }

    return {
      name,
      value: selfTime,
      total: cumTime || selfTime,
      children
    }
  }

  const root = build(rootName, 0)
  return { name: 'root', value: 0, total: root.total, children: [root] }
}

const activeTree = computed<FlamegraphNode | null>(() => {
  if (zoomedRoot.value) {
    return buildDynamicTree(zoomedRoot.value)
  }
  const tree = flamegraphTree.value
  if (!tree || tree.children.length <= 1) {
    return tree
  }
  // Show only the dominant entry point; smaller unrelated roots would
  // otherwise shrink the main call tree below canvas width.
  const biggest = tree.children.reduce((a, b) => (a.total >= b.total ? a : b))
  return { name: 'root', value: 0, total: biggest.total, children: [biggest] }
})

const activeTotalTime = computed(() => {
  if (zoomedRoot.value) {
    const hotspot = hotspotsByFunction.value.get(zoomedRoot.value)
    return hotspot ? hotspot.cumulative_time_ms / 1000 : totalTime.value
  }
  return totalTime.value
})
</script>

<template>
  <div class="profiling-flamegraph-app">
    <!-- Loading skeleton: CmkSkeleton tiles stand in for the summary bar, the
         flamegraph area, and the hotspots table until the async fetch returns. -->
    <div
      v-if="loading"
      class="profiling-flamegraph-app__skeleton"
      role="status"
      aria-live="polite"
      :aria-label="_t('Loading profile data')"
    >
      <CmkSkeleton type="box" width="100%" class="profiling-flamegraph-app__skeleton-bar" />
      <CmkSkeleton type="box" width="100%" class="profiling-flamegraph-app__skeleton-graph" />
      <div class="profiling-flamegraph-app__skeleton-table">
        <CmkSkeleton
          v-for="n in 8"
          :key="n"
          type="text"
          width="100%"
          class="profiling-flamegraph-app__skeleton-row"
        />
      </div>
    </div>

    <CmkAlert
      v-else-if="error"
      variant="error"
      :heading="_t('Failed to load profile data')"
      :text="untranslated(error)"
    />

    <template v-else>
      <!-- Compact summary bar with collapsible details -->
      <div v-if="metadata" class="profiling-flamegraph-app__summary-bar">
        <div class="profiling-flamegraph-app__summary-row">
          <CmkIconButton
            name="tree-closed"
            size="small"
            :title="headerExpanded ? _t('Hide details') : _t('Show details')"
            :aria-label="headerExpanded ? _t('Hide details') : _t('Show details')"
            :aria-expanded="headerExpanded"
            aria-controls="profiling-summary-details"
            :class="{ 'profiling-flamegraph-app__toggle--open': headerExpanded }"
            class="profiling-flamegraph-app__toggle"
            @click="headerExpanded = !headerExpanded"
          />
          <div
            class="profiling-flamegraph-app__summary-item"
            :title="_t('Elapsed real-world time of the HTTP request')"
          >
            <span class="profiling-flamegraph-app__summary-label">{{ _t('Wall') }}</span>
            <span class="profiling-flamegraph-app__summary-value--highlight">
              {{ metadata.duration_ms !== null ? formatMs(metadata.duration_ms) : '—' }}
            </span>
          </div>
          <div class="profiling-flamegraph-app__summary-item">
            <span class="profiling-flamegraph-app__summary-label">{{ _t('CPU') }}</span>
            <span class="profiling-flamegraph-app__summary-value">
              {{ formatMs(totalTime * 1000) }}
            </span>
          </div>
          <div
            class="profiling-flamegraph-app__summary-item profiling-flamegraph-app__summary-item--flex"
          >
            <CmkBadge size="small" color="default">{{
              sourceLabel(metadata.source_type)
            }}</CmkBadge>
            <span class="profiling-flamegraph-app__summary-value profiling-flamegraph-app__mono">
              {{ metadata.source_info }}
            </span>
          </div>
        </div>
        <!-- Expanded details (second row, below) -->
        <CmkCollapsible :open="headerExpanded" content-id="profiling-summary-details">
          <div class="profiling-flamegraph-app__summary-details">
            <div class="profiling-flamegraph-app__summary-item">
              <span class="profiling-flamegraph-app__summary-label">{{ _t('Recorded') }}</span>
              <span class="profiling-flamegraph-app__summary-value">
                {{ formatTimestamp(metadata.timestamp) }}
              </span>
            </div>
            <div class="profiling-flamegraph-app__summary-item">
              <span class="profiling-flamegraph-app__summary-label">{{ _t('Functions') }}</span>
              <span class="profiling-flamegraph-app__summary-value">
                {{ formatCount(totalFunctions) }}
              </span>
            </div>
            <div class="profiling-flamegraph-app__summary-item">
              <span class="profiling-flamegraph-app__summary-label">{{ _t('Calls') }}</span>
              <span class="profiling-flamegraph-app__summary-value">
                {{ formatCount(totalCalls) }}
              </span>
            </div>
          </div>
        </CmkCollapsible>
      </div>

      <!-- Sticky flamegraph section -->
      <div
        v-if="activeTree && activeTree.total > 0"
        class="profiling-flamegraph-app__flamegraph-sticky"
      >
        <FlamegraphCanvas
          :tree="activeTree!"
          :total-time="activeTotalTime"
          :search-query="graphSearchQuery"
          :highlight-function="highlightFunction"
          :callers-map="callersByFunction"
          :function-paths="functionPaths"
          @select-function="onGraphSelectFunction"
          @zoom-out="onGraphZoomOut"
        />
      </div>

      <!-- Search bar (between graph and table) — search left, chip middle, filter right -->
      <div v-if="activeTree && activeTree.total > 0" class="profiling-flamegraph-app__search-bar">
        <div class="profiling-flamegraph-app__search-wrap">
          <CmkInput
            v-model="graphSearchValue"
            field-size="medium"
            :placeholder="_t('Search flamegraph...')"
          />
          <CmkIconButton
            v-if="graphSearchValue"
            name="close"
            size="xsmall"
            :title="_t('Clear search')"
            :aria-label="_t('Clear search')"
            class="profiling-flamegraph-app__search-clear"
            @click="clearGraphSearch"
          />
        </div>

        <CmkChip
          v-if="highlightFunction"
          color="others"
          variant="outline"
          size="small"
          :title="`${_t('Selected (click to clear)')}: ${highlightFunction}`"
          class="profiling-flamegraph-app__selected-fn"
          @click="onGraphSelectFunction('')"
        >
          <span class="profiling-flamegraph-app__selected-fn-name">{{ highlightFunction }}</span>
          <template #end>
            <CmkIcon
              name="close"
              size="xsmall"
              :title="_t('Clear selection')"
              class="profiling-flamegraph-app__selected-fn-clear"
            />
          </template>
        </CmkChip>

        <div class="profiling-flamegraph-app__search-wrap">
          <CmkInput
            v-model="tableSearchValue"
            field-size="medium"
            :placeholder="_t('Filter table...')"
          />
          <CmkIconButton
            v-if="tableSearchValue"
            name="close"
            size="xsmall"
            :title="_t('Clear filter')"
            :aria-label="_t('Clear filter')"
            class="profiling-flamegraph-app__search-clear"
            @click="clearTableSearch"
          />
        </div>
      </div>

      <!-- Hotspots table -->
      <HotspotsTable
        v-if="hotspots.length > 0"
        :hotspots="hotspots"
        :highlight-function="highlightFunction"
        :search-query="tableSearchQuery"
        @select-function="onTableSelectFunction"
      />

      <div
        v-if="!activeTree || activeTree.total <= 0"
        class="profiling-flamegraph-app__empty-state"
      >
        {{ _t('No profiling data available') }}
      </div>
    </template>
  </div>
</template>

<style scoped>
.profiling-flamegraph-app {
  /* Reserved for the Checkmk main menu / header / breadcrumb above this view.
     Adjust here — not in the calc() below — if the surrounding chrome changes. */
  --profiling-chrome-offset: 180px;

  font-family: inherit;
  color: inherit;
  display: flex;
  flex-direction: column;

  /* Fit within remaining viewport — table scrolls internally, no page scroll. */
  height: calc(100vh - var(--profiling-chrome-offset));
  min-height: 400px;
  overflow: hidden;
}

/* Summary stats bar — compact, collapsible (expand downward) */
.profiling-flamegraph-app__summary-bar {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  padding: var(--spacing-half) var(--spacing);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  margin-bottom: var(--spacing-half);
  font-size: var(--font-size-small);
}

.profiling-flamegraph-app__summary-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing);
}

.profiling-flamegraph-app__summary-details {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing);
  padding-top: var(--spacing-half);
  border-top: var(--border-width-1) solid var(--ux-theme-5);
}

.profiling-flamegraph-app__toggle {
  transition: transform 0.15s;
  transform: rotate(0deg);
}

.profiling-flamegraph-app__toggle.profiling-flamegraph-app__toggle--open {
  transform: rotate(90deg);
}

.profiling-flamegraph-app__summary-item {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-half);
  white-space: nowrap;
}

.profiling-flamegraph-app__summary-item--flex {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.profiling-flamegraph-app__summary-label {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  font-weight: var(--font-weight-bold);
}

.profiling-flamegraph-app__summary-value {
  font-size: var(--font-size-normal);
}

.profiling-flamegraph-app__summary-value--highlight {
  font-weight: var(--font-weight-bold);
  font-family: monospace;
  font-size: var(--font-size-normal);
}

.profiling-flamegraph-app__mono {
  font-family: monospace;
  font-size: var(--font-size-normal);
  word-break: break-all;
}

/* Flamegraph section — fixed-size flex child, doesn't shrink. */
.profiling-flamegraph-app__flamegraph-sticky {
  flex: 0 0 auto;
  background: var(--ux-theme-2);
  padding-bottom: var(--spacing-half);
  margin-bottom: var(--spacing);
}

/* Search bar (below graph, above table) — graph search left, chip middle, table filter right */
.profiling-flamegraph-app__search-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  margin: var(--spacing-half) 0;
}

.profiling-flamegraph-app__search-wrap {
  position: relative;
  display: inline-block;
}

.profiling-flamegraph-app__search-bar .profiling-flamegraph-app__search-wrap:last-child {
  margin-left: auto;
}

.profiling-flamegraph-app__search-clear {
  position: absolute;
  right: var(--spacing-half);
  top: 50%;
  transform: translateY(-50%);
}

.profiling-flamegraph-app__selected-fn {
  max-width: 400px;
}

.profiling-flamegraph-app__selected-fn-clear {
  opacity: 0.55;
  transition: opacity 0.15s;
}

.profiling-flamegraph-app__selected-fn:hover .profiling-flamegraph-app__selected-fn-clear,
.profiling-flamegraph-app__selected-fn:focus-visible .profiling-flamegraph-app__selected-fn-clear {
  opacity: 1;
}

.profiling-flamegraph-app__selected-fn-name {
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 340px;
}

.profiling-flamegraph-app__empty-state {
  text-align: center;
  padding: var(--spacing-double);
  font-size: var(--font-size-large);
  color: var(--font-color-dimmed);
}

/* Skeleton loader — occupies the whole available flex space and lets the
 * table area grow/shrink so nothing is clipped on short viewports. */
.profiling-flamegraph-app__skeleton {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  padding: var(--spacing-half) 0;
}

.profiling-flamegraph-app__skeleton-bar {
  flex: 0 0 32px;
}

.profiling-flamegraph-app__skeleton-graph {
  flex: 0 0 260px;
}

.profiling-flamegraph-app__skeleton-table {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  margin-top: var(--spacing-half);
  overflow: hidden;
}

.profiling-flamegraph-app__skeleton-row {
  flex: 0 0 24px;
}
</style>
