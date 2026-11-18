<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { PanelConfig } from '@ucl/_ucl/components/detail-page'
import type { PanelState } from '@ucl/_ucl/types/prop-panel'
import type { BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'

import codeExample from './UclCmkBreadcrumbCodeExample.vue?raw'

const long1 = 'Production database cluster overview and health'
const long2 = 'CPU utilization, memory usage and network throughput'
const long3 = 'Aggregated performance metrics for all monitored nodes'
const long4 = 'A very long breadcrumb segment title that is truncated with an ellipsis'

const presets: Record<string, BreadcrumbItem[]> = {
  'all-short': [
    { title: 'Monitor', link: null },
    { title: 'Hosts', link: '#' },
    { title: 'Services', link: '#' },
    { title: 'CPU load', link: null }
  ],
  'long-last': [
    { title: 'Monitor', link: null },
    { title: 'Hosts', link: '#' },
    { title: 'Services', link: '#' },
    { title: long4, link: null }
  ],
  'long-mid': [
    { title: 'Monitor', link: null },
    { title: long2, link: '#' },
    { title: 'Services', link: '#' },
    { title: 'CPU load', link: null }
  ],
  'all-long': [
    { title: long1, link: null },
    { title: long2, link: '#' },
    { title: long3, link: '#' },
    { title: long4, link: null }
  ]
}

export const panelConfig = {
  preset: {
    type: 'list' as const,
    title: 'Segments',
    options: [
      { title: 'All short', name: 'all-short' },
      { title: 'Long last', name: 'long-last' },
      { title: 'Long middle', name: 'long-mid' },
      { title: 'All long', name: 'all-long' }
    ],
    initialState: 'long-last',
    help: 'When the row runs out of space the longest segment trims first; once it ties the next-longest they shrink together, down to all segments equal. The full title stays available via the segment title attribute (hover to reveal).'
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
import CmkBreadcrumb from 'cmk-ui-library/components/CmkBreadcrumb'
import { computed, ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref<PanelState>({ preset: panelConfig.preset.initialState })
const availableWidth = ref(480)

const items = computed<BreadcrumbItem[]>(
  () => presets[String(propState.value.preset)] ?? presets['all-short']!
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkBreadcrumb</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-breadcrumb">
        <p class="ucl-cmk-breadcrumb__hint">Drag the slider to resize the available space.</p>

        <label class="ucl-cmk-breadcrumb__slider">
          <span>Available width: {{ availableWidth }}px</span>
          <input
            v-model.number="availableWidth"
            type="range"
            min="200"
            max="1000"
            step="10"
            aria-label="Available width"
          />
        </label>

        <div class="ucl-cmk-breadcrumb__container" :style="{ width: `${availableWidth}px` }">
          <CmkBreadcrumb :items="items" />
        </div>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-breadcrumb {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  width: 100%;
}

.ucl-cmk-breadcrumb__hint {
  margin: 0;
  color: var(--font-color-dimmed);
}

.ucl-cmk-breadcrumb__slider {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  font-weight: var(--font-weight-bold);
}

.ucl-cmk-breadcrumb__slider input {
  width: 100%;
}

.ucl-cmk-breadcrumb__container {
  box-sizing: border-box;
  max-width: 100%;
  padding: var(--dimension-4);
  border: 1px dashed var(--default-border-color);
  border-radius: var(--border-radius);
  background: var(--ux-theme-2);
}
</style>
