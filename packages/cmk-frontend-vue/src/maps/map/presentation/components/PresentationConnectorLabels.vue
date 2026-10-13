<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { useMetricUnits } from '@/maps/map/composables/useMetricUnits'
import { usePerfometer } from '@/maps/map/composables/usePerfometer'
import type { ObjectState, ShapeElement } from '@/maps/types/api'

import { hasBinding, isMetriclessBinding } from '../binding'
import { connectorLabelVisible, flowVisual } from '../connectorFlow'

interface Pt {
  x: number
  y: number
}

const props = defineProps<{
  element: ShapeElement
  start: Pt
  end: Pt
  state: ObjectState | undefined
  connectionId?: string | null
}>()

const visForward = computed(() =>
  flowVisual(props.element, props.state, props.element.flow_metric ?? null, metricUnits.value)
)
const visBack = computed(() =>
  flowVisual(props.element, props.state, props.element.flow_metric_back ?? null, metricUnits.value)
)
const twoWay = computed(() => !!props.element.flow && !!props.element.flow_metric_back)

const labelShow = computed(() => connectorLabelVisible(props.element))
const pillFontSize = computed(() => props.element.label?.size ?? 11)
const pillColor = computed(() => props.element.label?.color || '#fff')
const pillBg = computed(() => props.element.label?.background || 'rgb(0 0 0 / 65%)')

// CMK perfometer for the bound service: supplies properly formatted values
// with units ("244 bit/s") where the raw perf_data has none. The bidirectional
// interface perfometer carries its two direction halves as sides. A one-way
// link with an explicit label text never reads the result, so it doesn't
// fetch either.
const labelBinding = {
  connectionId: () => props.connectionId,
  hostName: () => props.element.host_name,
  serviceDescription: () => props.element.service_description,
  perfData: () => props.state?.perf_data,
  checkCommand: () => props.state?.check_command,
  enabled: () =>
    labelShow.value &&
    hasBinding(props.element) &&
    !isMetriclessBinding(props.element) &&
    !!props.element.service_description &&
    (twoWay.value || !props.element.label?.text)
}
const perfometer = usePerfometer(labelBinding)
// Registered display units for the raw-metric fallback pills.
const metricUnits = useMetricUnits(labelBinding)

const cmkSplit = computed<[string | null, string | null]>(() => {
  const sides = perfometer.value?.sides ?? []
  return [sides[0]?.label ?? null, sides[1]?.label ?? null]
})

interface Pill {
  x: number
  y: number
  text: string
  w: number
  h: number
}

function lerp(t: number): Pt {
  return {
    x: props.start.x + (props.end.x - props.start.x) * t,
    y: props.start.y + (props.end.y - props.start.y) * t
  }
}

function pillFor(at: Pt, text: string): Pill {
  const h = Math.max(18, pillFontSize.value + 8)
  return {
    x: at.x,
    y: at.y,
    text,
    w: Math.max(28, text.length * pillFontSize.value * 0.72 + 12),
    h
  }
}

// A known utilization keeps its "%" display; only raw unitless values are
// upgraded to the CMK-formatted bandwidth string.
function directionText(vis: { util: number | null; valueText: string }, half: 0 | 1): string {
  if (vis.util !== null) {
    return vis.valueText
  }
  return cmkSplit.value[half] || vis.valueText
}

const pills = computed<Pill[]>(() => {
  if (!labelShow.value) {
    return []
  }
  if (!twoWay.value) {
    const text = props.element.label?.text || directionText(visForward.value, 0)
    return text ? [pillFor(lerp(0.5), text)] : []
  }
  const out: Pill[] = []
  const fwd = directionText(visForward.value, 0)
  const back = directionText(visBack.value, 1)
  if (fwd) {
    out.push(pillFor(lerp(0.25), fwd))
  }
  if (back) {
    out.push(pillFor(lerp(0.75), back))
  }
  return out
})
</script>

<template>
  <g>
    <g v-for="(pill, i) in pills" :key="i" :transform="`translate(${pill.x}, ${pill.y})`">
      <rect
        :x="-pill.w / 2"
        :y="-pill.h / 2"
        :width="pill.w"
        :height="pill.h"
        :rx="pill.h / 2"
        class="maps-presentation-connector-labels__pill-bg"
        :style="{ fill: pillBg }"
      />
      <text
        class="maps-presentation-connector-labels__pill-text"
        text-anchor="middle"
        dominant-baseline="central"
        :style="{ fill: pillColor, fontSize: `${pillFontSize}px` }"
      >
        {{ pill.text }}
      </text>
    </g>
  </g>
</template>

<style scoped>
.maps-presentation-connector-labels__pill-bg {
  pointer-events: none;
}

.maps-presentation-connector-labels__pill-text {
  font-weight: var(--font-weight-bold);
  pointer-events: none;
}
</style>
