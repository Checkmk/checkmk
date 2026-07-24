<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import TrendChartLegend from './TrendChartLegend.vue'
import TrendChartPlot from './TrendChartPlot.vue'
import {
  type CmkTrendChartProps,
  TREND_SERIES_PALETTE,
  type TrendChartSeriesWithColor
} from './types'

const props = defineProps<CmkTrendChartProps>()

const emit = defineEmits<{ seriesClick: [name: string] }>()

// The series keep their (ranked) order; colors are assigned by index and cycle
// through the palette, so the plot and the legend agree on each series' color.
const coloredSeries = computed<TrendChartSeriesWithColor[]>(() =>
  props.series.map((series, index) => ({
    ...series,
    color: TREND_SERIES_PALETTE[index % TREND_SERIES_PALETTE.length]!
  }))
)
</script>

<template>
  <div class="network-flow-cmk-trend-chart">
    <div class="network-flow-cmk-trend-chart__plot">
      <TrendChartPlot
        :series="coloredSeries"
        :display-mode="displayMode"
        :format-value="formatValue"
      />
    </div>
    <div class="network-flow-cmk-trend-chart__legend">
      <TrendChartLegend
        :series="coloredSeries"
        :format-value="formatValue"
        :clickable="clickableSeries"
        @name-click="emit('seriesClick', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.network-flow-cmk-trend-chart {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  container-type: size;
}

/* The plot takes the free space; the legend sits below at its natural height. */
.network-flow-cmk-trend-chart__plot {
  flex: 1;
  min-height: 0;
}

.network-flow-cmk-trend-chart__legend {
  flex: none;
}
</style>
