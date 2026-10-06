<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig, listOptions } from '@ucl/_ucl/components/detail-page'

import type { Scenario } from './graphScenarios'

type LegendPosition = 'bottom' | 'right'

const SCENARIO_TITLES: Record<Scenario, string> = {
  lines: 'Lines with gaps and thresholds',
  areas: 'Mirrored areas',
  stacked: 'Stacked areas and a line',
  bars: 'Bars per hour',
  'coarse-bars': 'Bars per hour on a six-hour grid',
  mixed: 'Stacked bars and a line'
}

const enabled = (title: string, help?: string) => ({
  type: 'boolean' as const,
  title,
  initialState: true,
  ...(help === undefined ? {} : { help })
})

export const panelConfig = {
  scenario: {
    type: 'list' as const,
    title: 'Scenario',
    help: 'Generated dummy data. A zoom or a pan generates the data of the new window.',
    options: listOptions<Scenario>(SCENARIO_TITLES),
    initialState: 'lines' as const
  },
  showTitle: enabled('Title'),
  showTimestamp: { type: 'boolean' as const, title: 'Timestamp', initialState: false },
  showConsolidation: {
    type: 'boolean' as const,
    title: 'Consolidation choice',
    initialState: false
  },
  showLegend: enabled('Legend'),
  legendPosition: {
    type: 'list' as const,
    title: 'Legend position',
    options: listOptions<LegendPosition>({
      bottom: 'Below the graph',
      right: 'Right of the graph'
    }),
    initialState: 'bottom' as const
  },
  showTimeAxis: enabled('Time axis'),
  showValueAxis: enabled('Value axis'),
  burger: enabled('Controls', 'The burger menu. Its entries are mocked and do nothing.'),
  zoom: enabled('Zoom'),
  panning: enabled('Panning'),
  brush: enabled('Brush', 'The overview strip below the graph.'),
  pin: enabled('Pin', 'A click on the plot sets the pin. The pin is mocked and not stored.'),
  width: { type: 'number' as const, title: 'Width (px)', initialState: 800 },
  height: {
    type: 'number' as const,
    title: 'Plot height (px)',
    help: 'The height of the plot; the header, the brush and the legend add to it.',
    initialState: 300
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { useMswWorker } from '@ucl/_ucl/composables/useMswWorker'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import type { AddTo, Interaction } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import { HttpResponse, http } from 'msw'
import { computed, ref, watch } from 'vue'

import GraphPanel from '@/graphing/components/GraphPanel.vue'
import { useBrushSnapshot } from '@/graphing/composables/useBrushSnapshot'
import type { BrushOverview, RequestedTimeRange, TimeRangeCommitKind } from '@/graphing/types'

import { scenarioData } from './graphScenarios'

defineProps<{ screenshotMode: boolean }>()

const HOUR = 3600

const { mockLoaded } = useMswWorker([
  http.get('*/domain-types/graph/actions/fetch_context_menu/invoke', () =>
    HttpResponse.json({
      value: [
        {
          heading: 'Export',
          items: [
            {
              label: 'Export as PNG',
              ariaLabel: 'Export as PNG',
              icon: 'download',
              action: { id: 'export', parameters: ['graph_image'] }
            }
          ]
        }
      ]
    })
  ),
  http.post('*/domain-types/graph/actions/export/invoke', () =>
    HttpResponse.json({ download_url: 'about:blank' })
  ),
  http.get('*/domain-types/graph/actions/get_pin/invoke', () =>
    HttpResponse.json({ pin_time: null })
  ),
  http.post('*/domain-types/graph/actions/set_pin/invoke', () => HttpResponse.json({}))
])

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const ADD_TO: AddTo = { type: 'graph', specification: {}, internal: '{}' }

const nowSeconds = (): number => Math.floor(Date.now() / 1000)

const requestedTimeRange = ref<RequestedTimeRange>({
  start: nowSeconds() - 25 * HOUR,
  end: nowSeconds()
})

const data = computed(() => scenarioData(propState.value.scenario, requestedTimeRange.value))

const status = (on: boolean): 'enabled' | 'disabled' => (on ? 'enabled' : 'disabled')

const interaction = computed<Interaction>(() => ({
  burger: status(propState.value.burger),
  zoom: status(propState.value.zoom),
  panning: status(propState.value.panning),
  hover: 'enabled',
  brush: status(propState.value.brush),
  pin: status(propState.value.pin)
}))

const brush = useBrushSnapshot<BrushOverview>({
  getNow: nowSeconds,
  getRequestedTimeRange: () => requestedTimeRange.value
})

watch(
  () => [brush.requestedDomain.value, propState.value.scenario] as const,
  ([domain, scenario]) => {
    const overview = scenarioData(scenario, domain)
    brush.onOverviewFetched({
      requestedDomain: domain,
      drawnDomain: domain,
      data: { metrics: overview.metrics, dataTimeRange: overview.dataTimeRange }
    })
  },
  { immediate: true }
)

function onRequestedTimeRange(range: RequestedTimeRange, kind: TimeRangeCommitKind): void {
  brush.onRangeCommitted(range, kind)
  requestedTimeRange.value = range
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Graph panel</UclDetailPageHeader>

    <UclDetailPageComponent>
      <GraphPanel
        v-if="mockLoaded"
        :key="propState.scenario"
        :metrics="data.metrics"
        :bin-unit="data.binUnit"
        :data-time-range="data.dataTimeRange"
        :requested-time-range="requestedTimeRange"
        :horizontal-lines="data.horizontalLines"
        :panel-key="0"
        :interaction="interaction"
        :title="SCENARIO_TITLES[propState.scenario]"
        :show-title="propState.showTitle"
        :show-timestamp="propState.showTimestamp"
        :show-consolidation="propState.showConsolidation"
        :show-legend="propState.showLegend"
        :legend-position="propState.legendPosition"
        :show-time-axis="propState.showTimeAxis"
        :show-value-axis="propState.showValueAxis"
        :figure-width="Math.max(200, propState.width)"
        :figure-height="Math.max(100, propState.height)"
        :brush-snapshot="brush.snapshot.value ?? undefined"
        :add-to="ADD_TO"
        @update:requested-time-range="onRequestedTimeRange"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>
  </UclDetailPageLayout>
</template>
