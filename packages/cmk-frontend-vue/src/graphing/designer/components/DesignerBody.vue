<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  CustomGraphDesignerMode,
  TitleMacroGroup
} from 'cmk-shared-typing/typescript/custom_graph_designer'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, ref, watch } from 'vue'

import { useGlobalRefresh } from '../../GlobalTimePicker/globalTimeState'
import GraphNotice from '../../components/GraphNotice.vue'
import GraphPanel from '../../components/GraphPanel.vue'
import {
  clippedToNavigableTime,
  navigableBounds
} from '../../components/TimeSeriesGraph/interaction/timeBounds'
import type { ConsolidationFn } from '../../components/consolidation'
import GraphLegend from '../../components/legend/GraphLegend.vue'
import { useBrushSnapshot } from '../../composables/useBrushSnapshot'
import { type GraphNoticeDescriptor, useGraphNotice } from '../../composables/useGraphNotice'
import { useRequestedTimeRange } from '../../composables/useRequestedTimeRange'
import type { RequestedTimeRange, TimeRange, TimeRangeCommitKind } from '../../types'
import type { CustomGraphMetric, CustomGraphOptions } from '../api'
import { MetricsCalculationSlideout, type RefVisibility } from '../calculation'
import { useCustomGraphData } from '../composables/useCustomGraphData'
import { useDeleteWithDependents } from '../composables/useDeleteWithDependents'
import type { GraphItemsStore } from '../composables/useGraphItems'
import { useItemValidation } from '../composables/useItemValidation'
import type { FormulaDraft, ItemId } from '../types'
import type { RowIssue } from '../validation'
import AppearanceTable from './AppearanceTable.vue'
import DeleteWithDependentsPopup from './DeleteWithDependentsPopup.vue'
import DesignerSettings from './DesignerSettings.vue'
import MetricsTable from './MetricsTable.vue'

/** Fallback until the container is measured (e.g. non-DOM test environments). */
const DEFAULT_FIGURE_WIDTH = 1000

const {
  store,
  graphOptions,
  title,
  mode,
  thresholds,
  metricBackendAvailable,
  createServicesAvailable,
  metricBackendDefaultTitle,
  titleMacros,
  issuesByRow
} = defineProps<{
  store: GraphItemsStore
  graphOptions: CustomGraphOptions
  title: string
  mode: CustomGraphDesignerMode
  thresholds: { warning: string; critical: string }
  metricBackendAvailable: boolean
  createServicesAvailable: boolean
  metricBackendDefaultTitle: string
  titleMacros: TitleMacroGroup[]
  issuesByRow: ReadonlyMap<ItemId, RowIssue[]>
}>()

const emit = defineEmits<{
  'update-graph-options': [graphOptions: CustomGraphOptions]
}>()

const displaySettings = defineModel<boolean>('displaySettings', { default: false })

const { _t } = usei18n()

const { validItems } = useItemValidation(store.items)

const consolidationFn = ref<ConsolidationFn>('max')
// The app seeds the global time range from the configured default before we mount.
const { requestedTimeRange, setRequestedTimeRange, timePickerRequests } = useRequestedTimeRange()

const brush = useBrushSnapshot<{ metrics: CustomGraphMetric[]; dataTimeRange: TimeRange }>({
  getNow: () => Math.floor(Date.now() / 1000),
  getRequestedTimeRange: () => requestedTimeRange.value
})

function onPanelTimeRange(requested: RequestedTimeRange, kind: TimeRangeCommitKind): void {
  const range = clippedToNavigableTime(requested, navigableBounds())
  brush.onRangeCommitted(range, kind)
  setRequestedTimeRange(range)
}

const hiddenMetricNames = ref<string[]>([])
const hiddenLineNames = ref<string[]>([])
const highlightedMetricName = ref<string | null>(null)

const graphContainer = ref<HTMLElement | null>(null)
const figureWidth = ref(DEFAULT_FIGURE_WIDTH)
const { observe } = useResizeObserver((entries) => {
  const width = entries[0]!.contentBoxSize![0]!.inlineSize
  if (width > 0) {
    figureWidth.value = Math.round(width)
  }
})
observe(graphContainer)

const data = useCustomGraphData({
  getItems: () => validItems.value,
  getGraphOptions: () => graphOptions,
  getRequestedTimeRange: () => requestedTimeRange.value,
  getConsolidationFn: () => consolidationFn.value,
  getFigureWidth: () => figureWidth.value,
  getOverviewRange: () => (mode === 'view' ? brush.requestedDomain.value : null),
  // Edit mode fetches hidden rows too, so the appearance table can show their stats.
  getFetchHidden: () => mode === 'edit'
})

const hiddenSourceIds = computed(
  () => new Set(store.items.value.filter((item) => !item.visible).map((item) => item.id))
)
/** The fetched series minus the ones whose source row is hidden — only these are drawn. */
const drawnMetrics = computed(() =>
  data.metrics.value.filter((metric) => !hiddenSourceIds.value.has(metric.source_id))
)
watch(
  () => data.overview.value,
  (overview) => {
    if (overview !== undefined) {
      brush.onOverviewFetched({
        requestedDomain: overview.requestedTimeRange,
        drawnDomain: overview.viewTimeRange,
        data: { metrics: overview.metrics, dataTimeRange: overview.dataTimeRange }
      })
    }
  }
)

const drawnBrushSnapshot = computed(() => {
  const snapshot = brush.snapshot.value
  if (snapshot === null) {
    return undefined
  }
  return {
    ...snapshot,
    data: {
      ...snapshot.data,
      metrics: snapshot.data.metrics.filter(
        (metric) => !hiddenSourceIds.value.has(metric.source_id)
      )
    }
  }
})

const fetchNotice = useGraphNotice({
  error: () => data.error.value,
  isLoading: () => data.isLoading.value,
  partialErrors: () => data.partialErrors.value,
  warnings: () => data.warnings.value
})

// A graph nobody has added a source to yet: the preview draws an empty frame, and this says what
// to do with it.
const emptyStateNotice = computed<GraphNoticeDescriptor | null>(() =>
  store.items.value.length === 0
    ? {
        variant: 'info',
        message: _t('No metrics added'),
        description: _t('Add a source to visualize your data')
      }
    : null
)

// A failed fetch outranks the empty state. The two barely overlap - with no rows there is no fetch
// to fail - but which wins should be stated rather than left to that coincidence.
const previewNotice = computed(() => fetchNotice.value ?? emptyStateNotice.value)

const { pauseRefresh } = useGlobalRefresh()
watch(
  () => mode,
  (newMode) => {
    if (newMode === 'edit') {
      hiddenMetricNames.value = []
      hiddenLineNames.value = []
    }
    data.refetch()
  }
)

const hasBlockingIssues = computed(() => issuesByRow.size > 0)

type Tab = 'appearance' | 'metrics'
const activeTab = ref<Tab>('metrics')
const TABS: { id: Tab; label: TranslatedString }[] = [
  { id: 'appearance', label: _t('Graph appearance') },
  { id: 'metrics', label: _t('Metrics selection') }
]

function onTabChange(value: string | number): void {
  if (value === 'appearance' || value === 'metrics') {
    activeTab.value = value
  }
}

const slideoutOpen = ref(false)

function applyRefVisibility(refVisibility: RefVisibility): void {
  if (refVisibility !== null) {
    store.setVisibility(refVisibility.ids, refVisibility.visible)
  }
}

function onCalculationAdd(draft: FormulaDraft, refVisibility: RefVisibility): void {
  store.addFormula(draft)
  applyRefVisibility(refVisibility)
}

function onCalculationUpdate(id: ItemId, draft: FormulaDraft, refVisibility: RefVisibility): void {
  store.updateFormula(id, draft)
  applyRefVisibility(refVisibility)
}

const calculationDelete = useDeleteWithDependents(store)

function onSettingsUpdate(newGraphOptions: CustomGraphOptions): void {
  emit('update-graph-options', newGraphOptions)
  displaySettings.value = false
}

const explicitRange = computed(() => {
  const range = graphOptions.explicit_vertical_range
  if (range?.type === 'fixed' && range.lower !== null && range.upper !== null) {
    return { min: range.lower, max: range.upper }
  }
  return null
})
</script>

<template>
  <div ref="graphContainer" class="graphing-designer-body">
    <DesignerSettings
      v-model:open="displaySettings"
      :graph-options="graphOptions"
      @update-settings="onSettingsUpdate"
    />

    <div class="graphing-designer-body__preview-container">
      <GraphPanel
        v-model:hidden-metric-names="hiddenMetricNames"
        v-model:hidden-line-names="hiddenLineNames"
        v-model:highlighted-metric-name="highlightedMetricName"
        class="graphing-designer-body__preview"
        :metrics="drawnMetrics"
        :data-time-range="data.dataTimeRange.value"
        :horizontal-lines="data.horizontalLines.value"
        :requested-time-range="requestedTimeRange"
        :time-picker-requests="timePickerRequests"
        :y-axis="explicitRange ? { explicit_range: explicitRange } : null"
        :title="title"
        show-title
        show-timestamp
        :figure-width="figureWidth"
        :figure-height="200"
        :show-legend="false"
        :interaction="{
          brush: mode === 'view' ? 'enabled' : 'disabled',
          burger: 'disabled',
          hover: 'enabled',
          panning: 'enabled',
          zoom: 'enabled',
          pin: 'enabled'
        }"
        :brush-snapshot="drawnBrushSnapshot"
        @update:requested-time-range="onPanelTimeRange"
        @inspect="pauseRefresh"
      />
      <GraphNotice
        v-if="previewNotice"
        v-bind="previewNotice"
        class="graphing-designer-body__notice"
        @retry="data.refetch()"
      />
    </div>

    <slot name="alerts" />

    <div class="graphing-designer-body__scroll-region">
      <GraphLegend
        v-if="mode === 'view'"
        v-model:hidden-metric-names="hiddenMetricNames"
        v-model:hidden-line-names="hiddenLineNames"
        fill-height
        :metrics="drawnMetrics"
        :horizontal-lines="data.horizontalLines.value"
        :consolidation-fn="consolidationFn"
        @hover-metric="highlightedMetricName = $event"
      />

      <CmkTabs
        v-else
        class="graphing-designer-body__tabs"
        :model-value="activeTab"
        :unmount-on-hide="false"
        @update:model-value="onTabChange"
      >
        <template #tabs>
          <CmkTab v-for="tab in TABS" :id="tab.id" :key="tab.id">
            <span class="graphing-designer-body__tab-label">
              <span
                v-if="tab.id === 'metrics' && hasBlockingIssues"
                class="graphing-designer-body__tab-icon"
              >
                <CmkIcon name="inline-error" size="large" aria-hidden="true" />
              </span>
              <span v-else-if="activeTab === tab.id" class="graphing-designer-body__tab-icon">
                <CmkMultitoneIcon name="checkmark" primary-color="font" size="small" />
              </span>
              {{ tab.label }}
            </span>
          </CmkTab>
        </template>
        <template #tab-contents>
          <CmkTabContent id="appearance" class="graphing-designer-body__tab-panel">
            <AppearanceTable
              :store="store"
              :metrics-by-source="data.metricsBySource.value"
              :resolved-titles="data.resolvedTitles.value"
            />
          </CmkTabContent>
          <CmkTabContent id="metrics" class="graphing-designer-body__tab-panel">
            <MetricsTable
              :store="store"
              :thresholds="thresholds"
              :metric-backend-available="metricBackendAvailable"
              :create-services-available="createServicesAvailable"
              :metric-backend-default-title="metricBackendDefaultTitle"
              :title-macros="titleMacros"
              :issues-by-row="issuesByRow"
              :resolved-titles="data.resolvedTitles.value"
              @add-calculation="slideoutOpen = true"
            />
          </CmkTabContent>
        </template>
      </CmkTabs>
    </div>

    <template v-if="mode === 'edit'">
      <MetricsCalculationSlideout
        :open="slideoutOpen"
        :items="validItems"
        :next-id="store.nextId.value"
        :next-color="store.nextColor.value"
        @add="onCalculationAdd"
        @update="onCalculationUpdate"
        @delete="(id) => calculationDelete.request([id])"
        @close="slideoutOpen = false"
      />

      <DeleteWithDependentsPopup
        v-if="calculationDelete.pending.value !== null"
        open
        :ids="calculationDelete.pending.value.ids"
        :dependents="calculationDelete.pending.value.dependents"
        @confirm="calculationDelete.confirm()"
        @close="calculationDelete.cancel()"
      />
    </template>
  </div>
</template>

<style scoped>
.graphing-designer-body {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 0;
  gap: var(--dimension-6);
  padding: var(--dimension-6);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);

  --graphing-designer-body-table-overflow: auto;
}

.graphing-designer-body__preview-container {
  position: relative;
  flex-shrink: 0;
}

.graphing-designer-body__preview {
  flex-shrink: 0;
}

.graphing-designer-body__notice {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 100%;
}

.graphing-designer-body__scroll-region {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 12rem;
}

.graphing-designer-body__tabs {
  flex: 0 1 auto;
  min-height: 0;
}

.graphing-designer-body__tab-panel:not([hidden]) {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 0;
  background: var(--ux-theme-2);
}

.graphing-designer-body__tab-label {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.graphing-designer-body__tab-icon {
  display: flex;
  line-height: 0;
}

@media (height < 945px) {
  .graphing-designer-body {
    flex-shrink: 0;

    --graphing-designer-body-table-overflow: visible;
  }
}
</style>
