<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'
import { max, range } from 'd3-array'
import { scaleBand, scaleLinear } from 'd3-scale'
import { computed } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { Barplot, BarplotBar, VisualContext } from '@/dashboard/types/widget'
import {
  stepIncrements,
  valueDomain
} from '@/graphing/components/TimeSeriesGraph/axes/tickStepping'

const props = defineProps<{
  value: Barplot
  width: number
  height: number
  filters: VisualContext
}>()

const MARGIN = { top: 20, right: 10, bottom: 10, left: 10 }
const TICK_SPACING = 85
const LABEL_HEIGHT = 12
const LABEL_OFFSET = 9
const BAR_OFFSET = 6

const plotWidth = computed(() => Math.max(props.width - MARGIN.left - MARGIN.right, 0))
const plotHeight = computed(() => Math.max(props.height - MARGIN.top - MARGIN.bottom, 0))

// The server sends the values in the user's temperature unit already.
const formatter = computed(() => userSpecificUnit(props.value.unit_format, 'celsius').formatter)

function formatValue(value: number): string {
  return formatter.value.render(value)
}

function formatTick(value: number): string {
  return (Math.abs(value) < 10e-16 ? '0' : formatValue(value)).replace(/\.0+\b/, '')
}

const hostNames = computed(() => [...new Set(props.value.bars.map((bar) => bar.host_name))])

const yScale = computed(() =>
  scaleBand<string>().domain(hostNames.value).range([plotHeight.value, 0]).padding(0.2)
)

const showLabels = computed(() => hostNames.value.length < plotHeight.value / LABEL_HEIGHT)

const xDomain = computed(() => {
  const tickCount = Math.max(2, Math.ceil(plotWidth.value / TICK_SPACING))
  const configured = props.value.range
  const domain: [number, number] =
    configured === null
      ? [0, max(props.value.bars, (bar) => bar.value ?? undefined) ?? 0]
      : [configured.minimum, configured.maximum]
  const stepping = props.value.unit_format.notation === 'iec' ? 'binary' : 'decimal'
  const [start, end, step] = valueDomain(domain, tickCount, stepIncrements(stepping))
  return { start, end, step }
})

const xScale = computed(() =>
  scaleLinear().domain([xDomain.value.start, xDomain.value.end]).range([0, plotWidth.value])
)

const ticks = computed(() => {
  const { start, end, step } = xDomain.value
  return range(start, end, step).map((tick) => ({
    x: xScale.value(tick),
    text: formatTick(tick)
  }))
})

const gridLines = computed(() => {
  const { start, end, step } = xDomain.value
  return range(start, end, step / 2).map((tick) => xScale.value(tick))
})

const barHeight = computed(() => Math.max(Math.min(24, yScale.value.bandwidth() - 12), 4))

function barY(bar: BarplotBar): number {
  return (yScale.value(bar.host_name) ?? 0) + BAR_OFFSET
}

function barWidth(bar: BarplotBar): number {
  return Math.max(0, xScale.value(bar.value ?? 0))
}

function barLabel(bar: BarplotBar): string {
  return bar.value === null ? bar.host_name : `${bar.host_name}: ${formatValue(bar.value)}`
}
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-barplot-figure"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <g :transform="`translate(${MARGIN.left}, ${MARGIN.top})`">
      <ContextualLinkTrigger
        v-for="(bar, index) in value.bars"
        :key="index"
        :links="value.links"
        :link-properties="bar.link_properties"
        :filters="filters"
      >
        <rect
          class="db-cmk-barplot-figure__bar"
          role="img"
          :aria-label="barLabel(bar)"
          x="0"
          :y="barY(bar)"
          :width="barWidth(bar)"
          :height="barHeight"
          rx="2"
        />
      </ContextualLinkTrigger>
      <text
        v-for="tick in ticks"
        :key="tick.x"
        class="db-cmk-barplot-figure__label"
        :x="tick.x"
        :y="-LABEL_OFFSET"
        aria-hidden="true"
      >
        {{ tick.text }}
      </text>
      <template v-if="showLabels">
        <text
          v-for="hostName in hostNames"
          :key="hostName"
          class="db-cmk-barplot-figure__label"
          :x="LABEL_OFFSET"
          :y="yScale(hostName)"
          dy="0.32em"
          aria-hidden="true"
        >
          {{ hostName }}
        </text>
      </template>
      <line
        v-for="x in gridLines"
        :key="x"
        class="db-cmk-barplot-figure__grid"
        :x1="x"
        :x2="x"
        y1="0"
        :y2="plotHeight"
        aria-hidden="true"
      />
    </g>
  </svg>
</template>

<style scoped>
.db-cmk-barplot-figure {
  display: block;
}

.db-cmk-barplot-figure__bar {
  fill: rgb(0 185 255 / 95%);
  stroke: rgb(0 0 0 / 20%);

  &:hover {
    fill: rgb(0 220 255 / 90%);
    stroke: black;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .db-cmk-barplot-figure__bar,
[data-theme='modern-dark'] .db-cmk-barplot-figure__bar:hover {
  fill: rgb(60 194 255);
}

.db-cmk-barplot-figure__label {
  fill: var(--font-color);
  font-size: 10px;
}

.db-cmk-barplot-figure__grid {
  stroke: rgb(128 151 177);
  stroke-opacity: 0.61;
  stroke-width: 0.5px;
}
</style>
