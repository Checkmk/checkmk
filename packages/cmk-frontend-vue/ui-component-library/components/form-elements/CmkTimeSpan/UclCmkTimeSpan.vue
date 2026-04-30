<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkTimeSpanCodeExample.vue?raw'

export const panelConfig = {
  showDay: { type: 'boolean', title: 'Show Days', initialState: true },
  showHour: { type: 'boolean', title: 'Show Hours', initialState: true },
  showMinute: { type: 'boolean', title: 'Show Minutes', initialState: true },
  showSecond: { type: 'boolean', title: 'Show Seconds', initialState: true },
  showMillisecond: { type: 'boolean', title: 'Show Milliseconds', initialState: false }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { computed, ref } from 'vue'

import CmkTimeSpan from '@/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'
import { type Magnitude } from '@/components/user-input/CmkTimeSpan/timeSpan'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
const data = ref<number | null>(0)

const displayedMagnitudes = computed<Magnitude[]>(() => {
  const result: Magnitude[] = []
  if (propState.value.showDay) {
    result.push('day')
  }
  if (propState.value.showHour) {
    result.push('hour')
  }
  if (propState.value.showMinute) {
    result.push('minute')
  }
  if (propState.value.showSecond) {
    result.push('second')
  }
  if (propState.value.showMillisecond) {
    result.push('millisecond')
  }
  return result
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTimeSpan</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTimeSpan
        v-model:data="data"
        :label="null"
        title="Duration"
        :input-hint="null"
        :displayed-magnitudes="displayedMagnitudes"
        :validators="[]"
        :backend-validation="[]"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
