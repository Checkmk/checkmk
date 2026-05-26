<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclTableCellBreakpoints.vue?raw'

export const a11yData = [
  {
    keys: ['—'],
    description:
      "No interactive affordances. The cell renders a plain <td> and inherits the table's keyboard semantics."
  }
]

const HIDE_BELOW_OPTIONS = [
  { title: 'Never (always visible)', name: 'never' },
  { title: 'S', name: 's' },
  { title: 'M', name: 'm' },
  { title: 'L', name: 'l' },
  { title: 'XL', name: 'xl' }
]

export const panelConfig = {
  defaultContent: {
    type: 'string' as const,
    title: 'default slot',
    initialState: '01',
    help: 'Rendered when even the S threshold is not satisfied.'
  },
  sContent: {
    type: 'string' as const,
    title: 'S slot',
    initialState: 'host-01'
  },
  mContent: {
    type: 'string' as const,
    title: 'M slot',
    initialState: 'host-01.example.com'
  },
  lContent: {
    type: 'string' as const,
    title: 'L slot',
    initialState: 'host-01.example.com (web)'
  },
  xlContent: {
    type: 'string' as const,
    title: 'XL slot',
    initialState: 'host-01.example.com — Linux web server'
  },
  hideBelow: {
    type: 'list' as const,
    title: 'hide-below',
    options: HIDE_BELOW_OPTIONS,
    initialState: 'never',
    help: 'Cell is hidden when the container width drops below this threshold.'
  },
  pxS: {
    type: 'number' as const,
    title: 'S = … px',
    initialState: 70,
    help: 'Pixel value passed to the cell whenever a slot or hide-below is set to "S".'
  },
  pxM: {
    type: 'number' as const,
    title: 'M = … px',
    initialState: 150
  },
  pxL: {
    type: 'number' as const,
    title: 'L = … px',
    initialState: 250
  },
  pxXL: {
    type: 'number' as const,
    title: 'XL = … px',
    initialState: 350
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, provide, ref } from 'vue'

import {
  type CellBreakpoints,
  MONITORING_TABLE_WIDTH
} from '@/monitoring/shared/components/MonitoringTableContext'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'

type TokenName = 's' | 'm' | 'l' | 'xl'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const SLIDER_MIN = 10

const sliderValue = ref<number>(propState.value.pxXL)
provide(MONITORING_TABLE_WIDTH, sliderValue)

const sliderMax = computed(() => Math.max(propState.value.pxXL * 1.5, sliderValue.value + 10, 600))

const trackWidth = computed(() => sliderMax.value - SLIDER_MIN)

const sliderFillPercent = computed(() => {
  const range = sliderMax.value - SLIDER_MIN
  if (range <= 0) {
    return 0
  }
  return ((sliderValue.value - SLIDER_MIN) / range) * 100
})

const sliderTrackBackground = computed(
  () =>
    `linear-gradient(to right, var(--success) 0%, var(--success) ${sliderFillPercent.value}%, var(--ux-theme-6) ${sliderFillPercent.value}%, var(--ux-theme-6) 100%)`
)

function tokenPx(token: TokenName): number {
  switch (token) {
    case 's':
      return propState.value.pxS
    case 'm':
      return propState.value.pxM
    case 'l':
      return propState.value.pxL
    case 'xl':
      return propState.value.pxXL
  }
}

const breakpoints = computed<CellBreakpoints>(() => ({
  S: propState.value.pxS,
  M: propState.value.pxM,
  L: propState.value.pxL,
  XL: propState.value.pxXL
}))

const hideBelow = computed<number | undefined>(() =>
  propState.value.hideBelow === 'never'
    ? undefined
    : tokenPx(propState.value.hideBelow as TokenName)
)

type Band = { name: string; start: number; end: number; isActive: boolean }

const activeBandName = computed(() => {
  const v = sliderValue.value
  if (v >= propState.value.pxXL) {
    return 'XL'
  }
  if (v >= propState.value.pxL) {
    return 'L'
  }
  if (v >= propState.value.pxM) {
    return 'M'
  }
  if (v >= propState.value.pxS) {
    return 'S'
  }
  return 'default'
})

const bands = computed<Band[]>(() => {
  const { pxS, pxM, pxL, pxXL } = propState.value
  const max = sliderMax.value
  const active = activeBandName.value
  const ranges = [
    { name: 'default', start: SLIDER_MIN, end: pxS },
    { name: 'S', start: pxS, end: pxM },
    { name: 'M', start: pxM, end: pxL },
    { name: 'L', start: pxL, end: pxXL },
    { name: 'XL', start: pxXL, end: max }
  ]
  return ranges.map((r) => ({ ...r, isActive: r.name === active }))
})

const currentWidth = computed(() => `${sliderValue.value} px`)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Table Cell breakpoints</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-table-cell-breakpoints__stack">
        <div class="ucl-table-cell-breakpoints__slider-controls">
          <div class="ucl-table-cell-breakpoints__slider-header">
            <span class="ucl-table-cell-breakpoints__slider-label">Container width</span>
            <span class="ucl-table-cell-breakpoints__current-width">
              <strong>{{ currentWidth }}</strong>
              → <code>{{ activeBandName }}</code> slot
            </span>
          </div>
          <div class="ucl-table-cell-breakpoints__track-scroll">
            <input
              v-model.number="sliderValue"
              type="range"
              :min="SLIDER_MIN"
              :max="sliderMax"
              :style="{ width: `${trackWidth}px`, background: sliderTrackBackground }"
              class="ucl-table-cell-breakpoints__slider"
            />
            <div class="ucl-table-cell-breakpoints__bands" :style="{ width: `${trackWidth}px` }">
              <div
                v-for="band in bands"
                :key="band.name"
                class="ucl-table-cell-breakpoints__band"
                :class="{ 'ucl-table-cell-breakpoints__band--active': band.isActive }"
                :style="{ width: `${Math.max(band.end - band.start, 0)}px` }"
                :title="`${band.start}–${band.end} px`"
              >
                {{ band.name }}
              </div>
            </div>
          </div>
        </div>

        <div
          class="ucl-table-cell-breakpoints__container"
          :style="{ width: `calc(${sliderValue}px + 2 * var(--dimension-4))` }"
        >
          <table class="ucl-table-cell-breakpoints__container-table">
            <tbody>
              <tr>
                <BaseCell :breakpoints="breakpoints" :hide-below="hideBelow">
                  <template #XL>{{ propState.xlContent }}</template>
                  <template #L>{{ propState.lContent }}</template>
                  <template #M>{{ propState.mContent }}</template>
                  <template #S>{{ propState.sContent }}</template>
                  <template #default>{{ propState.defaultContent }}</template>
                </BaseCell>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="ucl-table-cell-breakpoints__hint">
          Drag the slider to change the container width. The coloured bands beneath the track show
          which slot the cell selects at any given width; the active band is highlighted.
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-table-cell-breakpoints__stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-4);
  width: 100%;
}

.ucl-table-cell-breakpoints__slider-controls {
  width: 100%;
}

.ucl-table-cell-breakpoints__slider-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-2);
  margin-bottom: var(--dimension-2);
}

.ucl-table-cell-breakpoints__slider-label {
  font-weight: var(--font-weight-bold);
}

.ucl-table-cell-breakpoints__current-width {
  font-style: italic;
  opacity: 0.7;
}

.ucl-table-cell-breakpoints__track-scroll {
  overflow-x: auto;
  padding: var(--dimension-6) 0 var(--dimension-4);
}

.ucl-table-cell-breakpoints__slider {
  appearance: none;
  display: block;
  height: 6px;
  margin: 0 0 var(--dimension-4) 0;
  padding: 0;
  background: var(--ux-theme-6);
  border-radius: 3px;
  cursor: pointer;
}

.ucl-table-cell-breakpoints__slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-table-cell-breakpoints__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-table-cell-breakpoints__bands {
  display: flex;
  border: 1px solid var(--ux-theme-6);
  border-radius: 4px;
  overflow: hidden;
  height: 22px;
}

.ucl-table-cell-breakpoints__band {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 0 var(--dimension-1);
  font-size: var(--font-size-small);
  border-right: 1px solid var(--ux-theme-6);
  opacity: 0.55;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background: transparent;
}

.ucl-table-cell-breakpoints__band:last-child {
  border-right: none;
}

.ucl-table-cell-breakpoints__band--active {
  background: var(--ux-theme-4);
  opacity: 1;
  font-weight: var(--font-weight-bold);
}

.ucl-table-cell-breakpoints__container {
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  padding: var(--dimension-4);
  box-sizing: border-box;
  margin-left: calc(-1 * var(--dimension-4));
  max-width: 100%;
  overflow: hidden;
}

.ucl-table-cell-breakpoints__container-table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ucl-table-cell-breakpoints__container-table :deep(td) {
  padding: var(--dimension-2) var(--dimension-4);
  border: 1px solid var(--ux-theme-6);
}
/* stylelint-enable selector-pseudo-class-no-unknown */

.ucl-table-cell-breakpoints__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
