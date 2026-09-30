<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkPointerTooltip, {
  type CmkPointerTooltipPointer
} from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'
import { arc } from 'd3-shape'
import { computed, ref } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { Gauge, GaugeStatus, VisualContext } from '@/dashboard/types/widget'

import { valueFontSize } from './lib/valueFontSize'

const props = defineProps<{
  value: Gauge
  width: number
  height: number
  filters: VisualContext
  interactive: boolean
}>()

const { _t } = usei18n()

const MARGIN = 10
const LIMIT = (7 * Math.PI) / 12
const LABEL_ANGLE = (15 * Math.PI) / 24
const BIN_COUNT = 40
const MIN_HISTOGRAM_VALUES = 11
const STATE_FONT_SIZE = 14

type StateKind = GaugeStatus['state'] | 'PENDING'

const STATE_COLOR: Record<StateKind, string> = {
  OK: 'var(--color-state-ok)',
  WARNING: 'var(--color-state-warning)',
  CRITICAL: 'var(--color-state-critical)',
  UNKNOWN: 'var(--color-state-unknown)',
  PENDING: 'var(--color-state-pending)'
}

const SHORT_STATE: Record<StateKind, string> = {
  OK: 'OK',
  WARNING: 'WARN',
  CRITICAL: 'CRIT',
  UNKNOWN: 'UNKN',
  PENDING: 'PEND'
}

function arcPath(
  innerRadius: number,
  outerRadius: number,
  startAngle: number,
  endAngle: number
): string {
  return arc()({ innerRadius, outerRadius, startAngle, endAngle }) ?? ''
}

function splitUnit(rendered: string): { text: string; unit: string } {
  const [text, unit, ...rest] = rendered.split(' ')
  if (unit !== undefined && rest.length === 0) {
    return { text: text!, unit }
  }
  if (rendered.endsWith('%')) {
    return { text: rendered.slice(0, -1), unit: '%' }
  }
  return { text: rendered, unit: '' }
}

function binCounts(values: readonly number[], minimum: number, maximum: number): number[] {
  const binWidth = (maximum - minimum) / BIN_COUNT
  const counts = new Array<number>(BIN_COUNT).fill(0)
  for (const value of values) {
    if (value < minimum || value > maximum) {
      continue
    }
    counts[Math.min(Math.floor((value - minimum) / binWidth), BIN_COUNT - 1)]! += 1
  }
  return counts
}

const radius = computed(() =>
  Math.max(Math.min((props.width - 2 * MARGIN) / 2, (3 / 4) * (props.height - 2 * MARGIN)), 0)
)
const center = computed(() => ({ x: props.width / 2, y: radius.value + MARGIN }))

// The server sends the value in the user's temperature unit already.
const formatter = computed(() => userSpecificUnit(props.value.unit_format, 'celsius').formatter)

function angle(value: number): number {
  const { minimum, maximum } = props.value.range
  const clamped = Math.min(Math.max(value, minimum), maximum)
  return -LIMIT + ((clamped - minimum) / (maximum - minimum)) * 2 * LIMIT
}

const spanPath = computed(() => arcPath(radius.value * 0.75, radius.value * 0.85, -LIMIT, LIMIT))

const valueArc = computed(() =>
  props.value.value === null
    ? null
    : arcPath(radius.value * 0.75, radius.value * 0.85, -LIMIT, angle(props.value.value))
)

const valueText = computed(() =>
  props.value.value === null ? null : splitUnit(formatter.value.render(props.value.value))
)

const fontSize = computed(() => valueFontSize((radius.value * 5) / 3, radius.value / 2))
const valueFontSizePx = computed(() => `${fontSize.value}px`)

const rangeLabels = computed(() => {
  const distance = 0.8 * radius.value
  const y = -distance * Math.cos(LABEL_ANGLE)
  const x = distance * Math.sin(LABEL_ANGLE)
  return [
    { key: 'minimum', x: -x, y, text: formatter.value.render(props.value.range.minimum) },
    { key: 'maximum', x, y, text: formatter.value.render(props.value.range.maximum) }
  ]
})

const stateKind = computed<StateKind | null>(() => {
  const status = props.value.status
  if (status === null) {
    return null
  }
  return status.has_been_checked ? status.state : 'PENDING'
})

const statusBackground = computed(() => {
  if (!props.value.status?.tint_background) {
    return null
  }
  const backgroundRadius = radius.value * 0.69
  const start = (-13 * Math.PI) / 12
  const end = Math.PI / 12
  return (
    `M${backgroundRadius * Math.cos(start)},${backgroundRadius * Math.sin(start)}` +
    `A${backgroundRadius},${backgroundRadius},0,1,1,` +
    `${backgroundRadius * Math.cos(end)},${backgroundRadius * Math.sin(end)}Z`
  )
})

interface Bin {
  index: number
  path: string
  label: string
}

const bins = computed<Bin[]>(() => {
  const values = props.value.samples.map((sample) => sample.value)
  if (props.value.value !== null) {
    values.push(props.value.value)
  }
  if (values.length < MIN_HISTOGRAM_VALUES) {
    return []
  }
  const { minimum, maximum } = props.value.range
  const counts = binCounts(values, minimum, maximum)
  const fullest = Math.max(...counts)
  if (fullest === 0) {
    return []
  }
  const innerRadius = radius.value * 0.87
  const binAngle = (2 * LIMIT) / BIN_COUNT
  const binWidth = (maximum - minimum) / BIN_COUNT
  return counts.flatMap((count, index) => {
    if (count === 0) {
      return []
    }
    const start = -LIMIT + index * binAngle
    const share = ((100 * count) / values.length).toPrecision(3)
    const from = formatter.value.render(minimum + index * binWidth)
    const to = formatter.value.render(minimum + (index + 1) * binWidth)
    return [
      {
        index,
        path: arcPath(
          innerRadius,
          innerRadius + (radius.value - innerRadius) * (count / fullest) + 2,
          start,
          start + binAngle * 0.95
        ),
        label: `${share}%: ${from} – ${to}`
      }
    ]
  })
})

const hovered = ref<{ label: string; pointer: CmkPointerTooltipPointer } | null>(null)

function hover(bin: Bin, event: PointerEvent): void {
  hovered.value = { label: bin.label, pointer: { clientX: event.clientX, clientY: event.clientY } }
}
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-gauge-figure"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <g :transform="`translate(${center.x}, ${center.y})`">
      <path
        v-if="statusBackground && stateKind"
        class="db-cmk-gauge-figure__status-background"
        :d="statusBackground"
        :fill="STATE_COLOR[stateKind]"
        aria-hidden="true"
      />
      <path class="db-cmk-gauge-figure__span" :d="spanPath" aria-hidden="true" />
      <path
        v-if="valueArc"
        class="db-cmk-gauge-figure__value-arc"
        :d="valueArc"
        aria-hidden="true"
      />
      <text
        v-for="label in rangeLabels"
        :key="label.key"
        class="db-cmk-gauge-figure__range-label"
        :x="label.x"
        :y="label.y"
        text-anchor="middle"
      >
        {{ label.text }}
      </text>
      <path
        v-for="bin in bins"
        :key="bin.index"
        class="db-cmk-gauge-figure__bin"
        role="img"
        :aria-label="bin.label"
        :d="bin.path"
        @pointermove="hover(bin, $event)"
        @pointerleave="hovered = null"
      />
      <ContextualLinkTrigger
        v-if="valueText"
        :links="value.links"
        :link-properties="value.link_properties"
        :filters="filters"
        :interactive="interactive"
      >
        <text
          class="db-cmk-gauge-figure__value"
          x="0"
          :y="-radius / 10"
          text-anchor="middle"
          dominant-baseline="central"
        >
          <tspan>{{ valueText.text }}</tspan>
          <tspan
            v-if="valueText.unit"
            class="db-cmk-gauge-figure__unit"
            :dx="valueText.unit === '%' ? undefined : fontSize / 6"
            :dy="valueText.unit === '%' ? undefined : fontSize / 8"
          >
            {{ valueText.unit }}
          </tspan>
        </text>
      </ContextualLinkTrigger>
    </g>
    <g
      v-if="stateKind"
      :transform="`translate(${(width - STATE_FONT_SIZE * 8) / 2}, ${height - STATE_FONT_SIZE * 2})`"
    >
      <rect
        :width="STATE_FONT_SIZE * 8"
        :height="STATE_FONT_SIZE * 1.5"
        rx="2"
        :fill="STATE_COLOR[stateKind]"
        aria-hidden="true"
      />
      <text
        class="db-cmk-gauge-figure__state"
        :x="STATE_FONT_SIZE * 4"
        :y="STATE_FONT_SIZE * 1.1"
        text-anchor="middle"
      >
        {{ _t('Service: %{state}', { state: SHORT_STATE[stateKind] }) }}
      </text>
    </g>
  </svg>
  <CmkPointerTooltip :pointer="hovered?.pointer ?? null" @dismiss="hovered = null">
    {{ hovered?.label }}
  </CmkPointerTooltip>
</template>

<style scoped>
.db-cmk-gauge-figure {
  display: block;
}

.db-cmk-gauge-figure__status-background {
  opacity: 0.6;
}

.db-cmk-gauge-figure__span {
  fill: var(--ux-theme-5);
}

.db-cmk-gauge-figure__value-arc {
  fill: rgb(131 131 131);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .db-cmk-gauge-figure__value-arc {
  fill: var(--font-color);
}

.db-cmk-gauge-figure__range-label {
  fill: var(--font-color);
  font-size: 8pt;
}

.db-cmk-gauge-figure__bin {
  fill: #546679;
}

.db-cmk-gauge-figure__value {
  fill: var(--font-color);
  font-size: v-bind(valueFontSizePx);
  font-weight: bold;
}

.db-cmk-gauge-figure__unit {
  font-size: 0.5em;
  font-weight: lighter;
}

.db-cmk-gauge-figure__state {
  fill: black;
  font-size: 14px;
  font-weight: bold;
}
</style>
