<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import type { Colors, Sizes } from '@/components/progress/CmkProgressCircle.vue'

import codeExample from './UclRefreshCountdownCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Enter', 'Space'],
    description:
      'The countdown is a toggle button: pressing it pauses a running refresh or resumes a paused one. Its aria-label announces the current state and remaining seconds, and aria-pressed reflects the paused state.'
  }
]

export const panelConfig = {
  interval: {
    type: 'number' as const,
    title: 'Interval (s)',
    initialState: 30,
    help: 'Full refresh interval in seconds; the ring drains from this down to zero.'
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: [
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' }
    ] satisfies Options<NonNullable<Sizes>>[],
    initialState: 'medium' as const
  },
  color: {
    type: 'list' as const,
    title: 'Color',
    options: [
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Danger', name: 'danger' }
    ] satisfies Options<NonNullable<Colors>>[],
    initialState: 'success' as const
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
import { onMounted, onUnmounted, ref, watch } from 'vue'

import RefreshCountdown from '@/monitoring/shared/components/RefreshCountdown.vue'

const { screenshotMode } = defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const remaining = ref(propState.value.interval)
const paused = ref(false)

watch(
  () => propState.value.interval,
  (value) => {
    remaining.value = value
  }
)

let timer: number | undefined
onMounted(() => {
  if (screenshotMode) {
    return
  }
  timer = window.setInterval(() => {
    if (paused.value) {
      return
    }
    remaining.value = remaining.value <= 1 ? propState.value.interval : remaining.value - 1
  }, 1000)
})
onUnmounted(() => {
  if (timer) {
    window.clearInterval(timer)
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>RefreshCountdown</UclDetailPageHeader>

    <UclDetailPageComponent>
      <RefreshCountdown
        :remaining="remaining"
        :interval="propState.interval"
        :size="propState.size"
        :color="propState.color"
        :paused="paused"
        @toggle="paused = !paused"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
