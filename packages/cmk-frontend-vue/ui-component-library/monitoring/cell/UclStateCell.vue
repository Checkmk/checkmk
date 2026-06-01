<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import type { HostState } from '@/monitoring/shared/api/types.ts'

import codeExample from './UclStateCellCodeExample.vue?raw'

type StateName = HostState

const STATE_OPTIONS: Options<StateName>[] = [
  { title: 'UP', name: 'UP' },
  { title: 'DOWN', name: 'DOWN' },
  { title: 'UNREACHABLE', name: 'UNREACHABLE' }
]

export const panelConfig = {
  state: {
    type: 'list' as const,
    title: 'state',
    options: STATE_OPTIONS,
    initialState: 'UNREACHABLE' as StateName,
    help: 'The host state rendered by the cell.'
  },
  stale: {
    type: 'boolean' as const,
    title: 'stale',
    initialState: false,
    help: 'Show the stale indicator icon.'
  },
  pending: {
    type: 'boolean' as const,
    title: 'pending',
    initialState: false,
    help: 'Show the pending (reload) indicator icon.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, provide, ref } from 'vue'

import { MONITORING_TABLE_WIDTH } from '@/monitoring/shared/components/MonitoringTableContext'
import StateCell from '@/monitoring/shared/components/cell/StateCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const state = computed<HostState>(() => propState.value.state)

/** Width at which StateCell switches between the icon-only and labelled slot. */
const S_BREAKPOINT = 85

const SLIDER_MIN = 50
const SLIDER_MAX = 200

const sliderValue = ref<number>(150)

const COLUMN_MIN = 85
const COLUMN_MAX = 150

/** Resolved column width: the slider value clamped to the column's min/max. */
const effectiveWidth = computed(() => Math.min(Math.max(sliderValue.value, COLUMN_MIN), COLUMN_MAX))
provide(MONITORING_TABLE_WIDTH, effectiveWidth)

const sliderFillPercent = computed(
  () => ((sliderValue.value - SLIDER_MIN) / (SLIDER_MAX - SLIDER_MIN)) * 100
)

const sliderTrackBackground = computed(
  () =>
    `linear-gradient(to right, var(--success) 0%, var(--success) ${sliderFillPercent.value}%, var(--ux-theme-6) ${sliderFillPercent.value}%, var(--ux-theme-6) 100%)`
)

const currentWidth = computed(() => `${sliderValue.value} px`)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>StateCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-state-cell__stack">
        <div class="ucl-state-cell__slider-controls">
          <div class="ucl-state-cell__slider-header">
            <span class="ucl-state-cell__slider-label">Container width</span>
            <span class="ucl-state-cell__current-width">
              <strong>{{ currentWidth }}</strong>
            </span>
          </div>
          <input
            v-model.number="sliderValue"
            type="range"
            :min="SLIDER_MIN"
            :max="SLIDER_MAX"
            :style="{ background: sliderTrackBackground }"
            class="ucl-state-cell__slider"
          />
        </div>

        <div
          class="ucl-state-cell__container"
          :style="{ width: `calc(${sliderValue}px + 2 * var(--dimension-4))` }"
        >
          <table class="ucl-state-cell__container-table">
            <tbody>
              <tr>
                <StateCell :state="state" :stale="propState.stale" :pending="propState.pending" />
              </tr>
            </tbody>
          </table>
        </div>

        <p class="ucl-state-cell__hint">
          Drag the slider to change the container width. At or above {{ S_BREAKPOINT }} px the cell
          renders the state label next to the icon; below it the cell collapses to the icon only.
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-state-cell__stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--dimension-4);
  width: 100%;
  min-width: 0;
}

.ucl-state-cell__slider-controls {
  width: 100%;
}

.ucl-state-cell__slider-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-2);
  margin-bottom: var(--dimension-2);
}

.ucl-state-cell__slider-label {
  font-weight: var(--font-weight-bold);
}

.ucl-state-cell__current-width {
  font-style: italic;
  opacity: 0.7;
}

.ucl-state-cell__slider {
  appearance: none;
  display: block;
  width: 100%;
  height: 6px;
  margin: var(--dimension-6) 0 var(--dimension-4) 0;
  padding: 0;
  background: var(--ux-theme-6);
  border-radius: 3px;
  cursor: pointer;
}

.ucl-state-cell__slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-state-cell__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-state-cell__container {
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  padding: var(--dimension-4);
  box-sizing: border-box;
  margin-left: calc(-1 * var(--dimension-4));
  max-width: 100%;
  overflow: hidden;
}

.ucl-state-cell__container-table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
.ucl-state-cell__container-table :deep(td) {
  border: 1px solid var(--ux-theme-6);
  vertical-align: top;
}
/* stylelint-enable selector-pseudo-class-no-unknown */

.ucl-state-cell__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
