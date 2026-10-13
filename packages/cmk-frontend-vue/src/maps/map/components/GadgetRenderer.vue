<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { perfometerCaption } from '@/maps/map/composables/usePerfometer'
import type { MetricUnitMap, ObjectState, PerfometerResult } from '@/maps/types/api'
import { renderMetricValue } from '@/maps/utils/metricFormat'
import { getMetric, hasFillScale, parsePerfData, utilColor, utilPercent } from '@/maps/utils/perf'
import { stateColor } from '@/maps/utils/stateColors'

const props = defineProps<{
  type: string // 'gauge' | 'bar' | 'trafficlight' | 'value'
  metric?: string | null
  state: ObjectState | undefined
  size: number
  // CMK perfometer for the bound service. Supplies the fill percentage when
  // the raw perf_data carries no scale (no max/crit and not a % unit) and the
  // CMK-formatted value for the caption.
  perfometer?: PerfometerResult | null
  // Registered display units per raw perfdata label (CMK metric registry) —
  // the readout then matches the Checkmk GUI exactly.
  metricUnits?: MetricUnitMap | null
}>()

const metrics = computed(() => parsePerfData(props.state?.perf_data ?? ''))
const m = computed(() => getMetric(metrics.value, props.metric))
const pct = computed(() => (m.value ? utilPercent(m.value) : 0))
// Fill is proportional (NagVis scales to crit when there's no max). Metrics
// without any client-side scale fall back to the CMK perfometer percentage,
// which is computed from the plugin's focus_range.
const fillPct = computed(() => {
  if (m.value && !hasFillScale(m.value)) {
    return props.perfometer?.sides[0]?.pct ?? 0
  }
  return pct.value
})
// Colour by utilisation whenever there's a real scale (own max/crit/% unit or a
// CMK perfometer); otherwise fall back to the monitoring state colour.
const hasScale = computed(() => (m.value ? hasFillScale(m.value) : false) || !!props.perfometer)
const color = computed(() =>
  hasScale.value ? utilColor(fillPct.value) : stateColor(props.state?.state)
)

const valueLabel = computed(() =>
  m.value ? renderMetricValue(m.value.value, props.metricUnits?.[m.value.label], m.value.unit) : '—'
)

// Primary readout inside the gauge/bar: the metric value rendered exactly like
// Checkmk (vendored CMK formatter via the registry unit). A percent shows only
// when the unit genuinely is % — never faked from a bare `max` such as CPU
// load's core count. The CMK perfometer caption carries the titled context below.
const readout = computed(() => valueLabel.value)
const caption = computed(() => (props.perfometer ? perfometerCaption(props.perfometer) : ''))

// The raw-value gadget scales on its own label since it never shows a percentage.
const rawScale = computed(() => {
  const n = valueLabel.value.length
  if (n <= 4) {
    return 1
  }
  if (n <= 6) {
    return 0.85
  }
  if (n <= 8) {
    return 0.7
  }
  return 0.55
})

// Shrink the readout font for long absolute values so e.g. "512 MB" still fits.
const readoutScale = computed(() => {
  const n = readout.value.length
  if (n <= 3) {
    return 1
  }
  if (n <= 5) {
    return 0.78
  }
  if (n <= 7) {
    return 0.62
  }
  return 0.5
})

const monState = computed(() => props.state?.state ?? 'PENDING')
const isRed = computed(() => ['DOWN', 'CRITICAL'].includes(monState.value))
const isAmber = computed(() => ['WARNING', 'UNKNOWN', 'UNREACHABLE'].includes(monState.value))
const isGreen = computed(() => ['UP', 'OK'].includes(monState.value))

// Bulb style: lit = solid colored glow; unlit = slightly lighter than the dark housing + colored ring
// The bulbs always sit inside the dark housing (rgba(0,0,0,0.55)), so contrast against
// the housing — not the map background — is what matters here.
function bulbStyle(active: boolean, rgb: string): Record<string, string> {
  if (active) {
    return {
      background: `rgb(${rgb})`,
      boxShadow: `0 0 10px 2px rgba(${rgb},0.7)`
    }
  }
  return {
    background: 'rgba(255,255,255,0.07)',
    boxShadow: `inset 0 0 0 1.5px rgba(${rgb},0.55), inset 0 0 6px rgba(${rgb},0.2)`
  }
}

// Gauge arc helpers (180° sweep from left to right)
const R = computed(() => props.size * 0.4)
const cx = computed(() => props.size / 2)
const cy = computed(() => props.size * 0.55)

function polarX(angle: number) {
  return cx.value + R.value * Math.cos((angle * Math.PI) / 180)
}
function polarY(angle: number) {
  return cy.value + R.value * Math.sin((angle * Math.PI) / 180)
}

const START = 180
const SWEEP = 180

const bgArc = computed(() => {
  const ex = polarX(START + SWEEP),
    ey = polarY(START + SWEEP)
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 0 1 ${ex} ${ey}`
})

const valArc = computed(() => {
  const sweep = (fillPct.value / 100) * SWEEP
  if (sweep < 1) {
    return ''
  }
  const ex = polarX(START + sweep),
    ey = polarY(START + sweep)
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 0 1 ${ex} ${ey}`
})
</script>

<template>
  <div
    v-if="type === 'trafficlight'"
    class="maps-gadget-renderer__traffic"
    style="
      background: var(--maps-map-view-gadget-bg);
      border-color: var(--maps-map-view-gadget-ring);
    "
    :style="{ gap: `${Math.max(2, size * 0.08)}px`, padding: `${Math.max(4, size * 0.12)}px` }"
  >
    <div
      class="maps-gadget-renderer__bulb"
      :style="{
        ...bulbStyle(isRed, '239,68,68'),
        width: `${size * 0.55}px`,
        height: `${size * 0.55}px`
      }"
    />
    <div
      class="maps-gadget-renderer__bulb"
      :style="{
        ...bulbStyle(isAmber, '255,208,0'),
        width: `${size * 0.55}px`,
        height: `${size * 0.55}px`
      }"
    />
    <div
      class="maps-gadget-renderer__bulb"
      :style="{
        ...bulbStyle(isGreen, '34,197,94'),
        width: `${size * 0.55}px`,
        height: `${size * 0.55}px`
      }"
    />
  </div>

  <div
    v-else-if="type === 'bar'"
    class="maps-gadget-renderer__stack"
    :style="{ width: `${size}px`, gap: `${Math.max(2, size * 0.05)}px` }"
  >
    <div
      class="maps-gadget-renderer__track"
      style="background: var(--maps-map-view-gadget-bar-bg)"
      :style="{
        height: `${Math.max(10, Math.round(size * 0.22))}px`,
        boxShadow: 'inset 0 0 0 1px var(--maps-map-view-gadget-ring)'
      }"
    >
      <div
        class="maps-gadget-renderer__fill"
        :style="{ width: `${fillPct}%`, background: color }"
      />
      <span
        class="maps-gadget-renderer__pct"
        style="
          color: var(--maps-map-view-gadget-ink);
          text-shadow: var(--maps-map-view-text-outline);
        "
        :style="{ fontSize: `${Math.max(8, Math.round(size * 0.13 * readoutScale))}px` }"
        >{{ readout }}</span
      >
    </div>
    <span
      v-if="caption"
      style="
        color: var(--maps-map-view-gadget-ink-dim);
        text-shadow: var(--maps-map-view-text-outline);
      "
      class="maps-gadget-renderer__value maps-gadget-renderer__value--bar"
      :style="{ fontSize: `${Math.max(8, Math.round(size * 0.13))}px` }"
      >{{ caption }}</span
    >
  </div>

  <!-- Raw value (NagVis rawNumbers): the metric reading as bare state-coloured text -->
  <div v-else-if="type === 'value'" class="maps-gadget-renderer__stack">
    <span
      class="maps-gadget-renderer__raw"
      :style="{
        color: stateColor(state?.state),
        fontSize: `${Math.max(11, Math.round(size * 0.32 * rawScale))}px`
      }"
      >{{ valueLabel }}</span
    >
  </div>

  <div v-else class="maps-gadget-renderer__stack">
    <svg :width="size" :height="size * 0.65" :viewBox="`0 0 ${size} ${size * 0.65}`">
      <!-- The track colour is a token, so it is styled rather than set as a
           presentation attribute, which cannot resolve var(). -->
      <path
        class="maps-gadget-renderer__gauge-track"
        :d="bgArc"
        fill="none"
        stroke-width="8"
        stroke-linecap="round"
      />
      <path
        :d="valArc"
        fill="none"
        :stroke="color"
        stroke-width="8"
        stroke-linecap="round"
        class="maps-gadget-renderer__arc"
      />
      <text
        :x="size / 2"
        :y="size * 0.55"
        text-anchor="middle"
        font-weight="700"
        :style="{
          fill: 'var(--maps-map-view-gadget-ink)',
          fontSize: `${size * 0.18 * readoutScale}px`
        }"
        stroke="rgb(0 0 0 / 0.9)"
        :stroke-width="size * 0.05"
        stroke-linejoin="round"
        paint-order="stroke"
      >
        {{ readout }}
      </text>
    </svg>
    <span
      v-if="caption"
      style="
        color: var(--maps-map-view-gadget-ink-dim);
        text-shadow: var(--maps-map-view-text-outline);
      "
      class="maps-gadget-renderer__value"
      :style="{ fontSize: '9px', maxWidth: `${size}px` }"
      >{{ caption }}</span
    >
  </div>
</template>

<style scoped>
.maps-gadget-renderer__gauge-track {
  stroke: var(--maps-map-view-gauge-track);
}

.maps-gadget-renderer__traffic {
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: var(--dimension-5);
  box-shadow: 0 0 0 1px currentcolor;
}

.maps-gadget-renderer__bulb {
  border-radius: 9999px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.maps-gadget-renderer__stack {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.maps-gadget-renderer__track {
  position: relative;
  overflow: hidden;
  width: 100%;
  border-radius: 9999px;
}

.maps-gadget-renderer__fill {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  border-radius: 9999px;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.maps-gadget-renderer__pct {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-bold);
}

.maps-gadget-renderer__raw {
  font-weight: var(--font-weight-bold);
  line-height: 1.1;
  white-space: nowrap;
  text-shadow: var(--maps-map-view-text-outline);
}

.maps-gadget-renderer__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-gadget-renderer__value--bar {
  width: 100%;
  text-align: center;
}

.maps-gadget-renderer__arc {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
