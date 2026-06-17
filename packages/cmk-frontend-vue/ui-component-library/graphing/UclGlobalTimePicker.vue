<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { computed, ref } from 'vue'

import GlobalTimePickerApp from '@/graphing/GlobalTimePicker/GlobalTimePickerApp.vue'

import codeExample from './UclGlobalTimePickerCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

const HOUR = 3600
const DAY = 24 * HOUR

const props: GlobalTimePickerProps = {
  custom_time_ranges: [
    { title: 'Last 1 hour', total_seconds: HOUR },
    { title: 'Last 6 hours', total_seconds: 6 * HOUR },
    { title: 'Last 24 hours', total_seconds: 24 * HOUR },
    { title: 'Last 8 days', total_seconds: 8 * DAY },
    { title: 'Last 32 days', total_seconds: 32 * DAY }
  ],
  default_time_range: 4 * HOUR,
  server_time_zone: 'America/Los_Angeles'
}

const SLIDER_MIN = 440
const SLIDER_MAX = 960
const containerWidth = ref<number>(620)

const sliderFillPercent = computed(() => {
  const range = SLIDER_MAX - SLIDER_MIN
  return range <= 0 ? 0 : ((containerWidth.value - SLIDER_MIN) / range) * 100
})

const sliderTrackBackground = computed(
  () =>
    `linear-gradient(to right, var(--success) 0%, var(--success) ${sliderFillPercent.value}%, var(--ux-theme-6) ${sliderFillPercent.value}%, var(--ux-theme-6) 100%)`
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Global time picker</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-global-time-picker__stack">
        <div class="ucl-global-time-picker__controls">
          <div
            class="ucl-global-time-picker__controls-header"
            :style="{ width: `${containerWidth}px` }"
          >
            <span class="ucl-global-time-picker__label">Container width</span>
            <span class="ucl-global-time-picker__readout">
              <strong>{{ containerWidth }} px</strong>
            </span>
          </div>
          <input
            v-model.number="containerWidth"
            type="range"
            :min="SLIDER_MIN"
            :max="SLIDER_MAX"
            :style="{ maxWidth: `${SLIDER_MAX}px`, background: sliderTrackBackground }"
            class="ucl-global-time-picker__slider"
          />
        </div>

        <div class="ucl-global-time-picker__viewport" :style="{ width: `${containerWidth}px` }">
          <GlobalTimePickerApp v-bind="props" />
        </div>

        <p class="ucl-global-time-picker__hint">
          Drag the slider to narrow the container. As space runs out, the quick-range chips collapse
          from the right into the "More ranges" overflow menu; widen it again and they return.
        </p>
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-global-time-picker__stack {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
  width: 100%;
}

.ucl-global-time-picker__controls {
  width: 100%;
  max-width: 100%;
}

.ucl-global-time-picker__controls-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-2);
  max-width: 100%;
  margin-bottom: var(--dimension-2);
}

.ucl-global-time-picker__label {
  font-weight: var(--font-weight-bold);
}

.ucl-global-time-picker__readout {
  font-style: italic;
  opacity: 0.7;
}

.ucl-global-time-picker__slider {
  appearance: none;
  display: block;
  width: 100%;
  height: 6px;
  margin: var(--dimension-4) 0 0;
  padding: 0;
  background: var(--ux-theme-6);
  border-radius: 3px;
  cursor: pointer;
}

.ucl-global-time-picker__slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-global-time-picker__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-global-time-picker__viewport {
  box-sizing: content-box;
  max-width: 100%;
  padding: var(--dimension-4);
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
}

.ucl-global-time-picker__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
