<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { AlertOverview, AlertOverviewElement, VisualContext } from '@/dashboard/types/widget'

import FigureTooltip, { type FigureTooltipContent } from './lib/FigureTooltip.vue'
import HexagonGridFigure, { type HexagonCell } from './lib/HexagonGridFigure.vue'
import { HEXAGON_MAX_BOX_WIDTH, type HexagonStyle } from './lib/hexagon'

const props = defineProps<{
  value: AlertOverview
  width: number
  height: number
  filters: VisualContext
  interactive: boolean
}>()

const { _t, _tn } = usei18n()

const HEXAGON_SCALE = 1.06
const MIN_UPPER_BOUND = 100
const COLOR_STEPS = 16

const STEP_STYLES: readonly HexagonStyle[] = Array.from({ length: COLOR_STEPS }, (_, step) => ({
  color: `color-mix(in srgb, #083775 ${(step / (COLOR_STEPS - 1)) * 100}%, #b1d2e8)`,
  fillOpacity: 0.4,
  strokeOpacity: 0
}))

function title(element: AlertOverviewElement): string {
  return element.service_description === null
    ? element.host_name
    : `${element.host_name} - ${element.service_description}`
}

const upperBound = computed(() =>
  Math.max(MIN_UPPER_BOUND, ...props.value.elements.map((element) => element.num_problems + 1))
)

const cells = computed<HexagonCell[]>(() =>
  props.value.elements.map((element) => ({
    label: title(element),
    outer: {
      style:
        STEP_STYLES[Math.round((element.num_problems / upperBound.value) * (COLOR_STEPS - 1))]!,
      scale: HEXAGON_SCALE
    },
    inner: null,
    links: element.links,
    linkProperties: element.link_properties
  }))
)

const figureLabel = computed(() =>
  _tn('%{n} object with alerts', '%{n} objects with alerts', props.value.elements.length, {
    n: props.value.elements.length
  })
)

function tooltip(index: number): FigureTooltipContent {
  const element = props.value.elements[index]!
  return {
    title: title(element),
    state: null,
    rows: [
      { key: 'problems', count: element.num_problems, text: _t('Problems in total') },
      { key: 'critical', count: element.num_crit, text: _t('Critical') },
      { key: 'unknown', count: element.num_unknown, text: _t('Unknown') },
      { key: 'warning', count: element.num_warn, text: _t('Warning') }
    ]
  }
}
</script>

<template>
  <HexagonGridFigure
    :label="figureLabel"
    :cells="cells"
    :width="width"
    :height="height"
    :max-box-width="HEXAGON_MAX_BOX_WIDTH.default"
    :filters="filters"
    :interactive="interactive"
  >
    <template #tooltip="{ index }">
      <FigureTooltip v-bind="tooltip(index)" />
    </template>
  </HexagonGridFigure>
</template>
