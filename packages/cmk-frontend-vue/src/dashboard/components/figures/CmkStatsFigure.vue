<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { LinkProperties, Stats, StatsPart, VisualContext } from '@/dashboard/types/widget'

import { hexagonPath, nestedRings } from './lib/hexagon'

const props = defineProps<{
  value: Stats
  width: number
  height: number
  filters: VisualContext
  interactive: boolean
}>()

const { _t } = usei18n()

type StatsCategory = StatsPart['category']

const HEXAGON_RADIUS = 48
const ROW_HEIGHT = 20
const COUNT_WIDTH = 40
const BOX_WIDTH = 5
const BOX_HEIGHT = 14
const BOX_BORDER = 1
const COLUMN_GAP = 6
const TITLE_WIDTH = 115
const TABLE_WIDTH = COUNT_WIDTH + COLUMN_GAP + BOX_WIDTH + COLUMN_GAP + TITLE_WIDTH

interface CategoryStyle {
  color: string
  fillOpacity: number
  strokeOpacity: number
}

const STYLE: Record<StatsCategory, CategoryStyle> = {
  up: { color: 'var(--success)', fillOpacity: 0.06, strokeOpacity: 0.9 },
  ok: { color: 'var(--success)', fillOpacity: 0.06, strokeOpacity: 0.9 },
  downtime: { color: 'var(--color-light-blue-50)', fillOpacity: 0.6, strokeOpacity: 1 },
  unreachable: { color: 'var(--color-orange-50)', fillOpacity: 0.8, strokeOpacity: 1 },
  down: { color: 'var(--color-dark-red-50)', fillOpacity: 0.8, strokeOpacity: 1 },
  host_down: { color: 'var(--color-dark-blue-50)', fillOpacity: 0.5, strokeOpacity: 1 },
  warning: { color: 'var(--color-yellow-50)', fillOpacity: 0.6, strokeOpacity: 1 },
  unknown: { color: 'var(--color-orange-50)', fillOpacity: 0.8, strokeOpacity: 1 },
  critical: { color: 'var(--color-dark-red-50)', fillOpacity: 0.8, strokeOpacity: 1 }
}

const TITLE: Record<StatsCategory, string> = {
  up: _t('Up'),
  ok: _t('OK'),
  downtime: _t('In downtime'),
  unreachable: _t('Unreachable'),
  down: _t('Down'),
  host_down: _t('On down host'),
  warning: _t('Warning'),
  unknown: _t('Unknown'),
  critical: _t('Critical')
}

interface Ring {
  category: StatsCategory
  path: string
  label: string
}

const rings = computed<Ring[]>(() =>
  nestedRings(props.value.parts, HEXAGON_RADIUS)
    .filter(({ part }) => part.count > 0)
    .map(({ part, radius }) => ({
      category: part.category,
      path: hexagonPath(radius),
      label: `${TITLE[part.category]}: ${part.count}`
    }))
)

interface Row {
  key: string
  count: number
  title: string
  color: string
  linkProperties: LinkProperties
}

const rows = computed<Row[]>(() => [
  ...props.value.parts.map((part) => ({
    key: part.category,
    count: part.count,
    title: TITLE[part.category],
    color: STYLE[part.category].color,
    linkProperties: part.link_properties
  })),
  {
    key: 'total',
    count: props.value.total.count,
    title: _t('Total'),
    color: 'currentColor',
    linkProperties: props.value.total.link_properties
  }
])

const hexagonCenter = computed(() => ({ x: props.width / 4, y: props.height / 2 }))

const tableOrigin = computed(() => ({
  x: props.width / 2 + Math.max((props.width / 2 - TABLE_WIDTH) / 2, 0),
  y: props.height / 2 - (rows.value.length * ROW_HEIGHT) / 2
}))

function rowTransform(index: number): string {
  return `translate(${tableOrigin.value.x}, ${tableOrigin.value.y + index * ROW_HEIGHT})`
}
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-stats-figure"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <g :transform="`translate(${hexagonCenter.x}, ${hexagonCenter.y})`">
      <path
        v-if="value.total.count === 0"
        class="db-cmk-stats-figure__empty"
        :d="hexagonPath(HEXAGON_RADIUS)"
        aria-hidden="true"
      />
      <template v-else>
        <path
          v-for="ring in rings"
          :key="ring.category"
          role="img"
          :aria-label="ring.label"
          :d="ring.path"
          :fill="STYLE[ring.category].color"
          :fill-opacity="STYLE[ring.category].fillOpacity"
          :stroke="STYLE[ring.category].color"
          :stroke-opacity="STYLE[ring.category].strokeOpacity"
        />
      </template>
    </g>
    <ContextualLinkTrigger
      v-for="(row, index) in rows"
      :key="row.key"
      :links="value.links"
      :link-properties="row.linkProperties"
      :filters="filters"
      :interactive="interactive"
    >
      <g :transform="rowTransform(index)">
        <text
          class="db-cmk-stats-figure__legend-text"
          :x="COUNT_WIDTH"
          :y="ROW_HEIGHT / 2"
          text-anchor="end"
          dominant-baseline="central"
          fill="currentColor"
        >
          {{ row.count }}
        </text>
        <rect
          class="db-cmk-stats-figure__legend-box"
          :x="COUNT_WIDTH + COLUMN_GAP + BOX_BORDER / 2"
          :y="(ROW_HEIGHT - BOX_HEIGHT + BOX_BORDER) / 2"
          :width="BOX_WIDTH - BOX_BORDER"
          :height="BOX_HEIGHT - BOX_BORDER"
          rx="2"
          :style="{ '--box-color': row.color }"
          aria-hidden="true"
        />
        <text
          class="db-cmk-stats-figure__legend-text"
          :x="COUNT_WIDTH + COLUMN_GAP + BOX_WIDTH + COLUMN_GAP"
          :y="ROW_HEIGHT / 2"
          dominant-baseline="central"
          fill="currentColor"
        >
          {{ row.title }}
        </text>
      </g>
    </ContextualLinkTrigger>
  </svg>
</template>

<style scoped>
.db-cmk-stats-figure {
  display: block;
}

.db-cmk-stats-figure__legend-box {
  fill: var(--box-color);
  stroke: color-mix(in srgb, var(--box-color) 70%, black);
  stroke-width: 1px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .db-cmk-stats-figure__legend-box {
  stroke: var(--box-color);
}

a:hover .db-cmk-stats-figure__legend-text {
  text-decoration: underline;
}

.db-cmk-stats-figure__empty {
  fill: currentcolor;
  fill-opacity: 0.05;
  stroke: currentcolor;
  stroke-opacity: 0.2;
}
</style>
