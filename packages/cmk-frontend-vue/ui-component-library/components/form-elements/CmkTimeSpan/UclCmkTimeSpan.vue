<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type BoolPropDef, type PanelConfigFor } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkTimeSpanCodeExample.vue?raw'

type OmittedProps = 'modelValue' | 'ariaLabel' | 'title' | 'externalErrors' | 'displayedMagnitudes'
type AdditionalProps = {
  showDay: BoolPropDef
  showHour: BoolPropDef
  showMinute: BoolPropDef
  showSecond: BoolPropDef
  showMillisecond: BoolPropDef
}

export const panelConfig = {
  label: { type: 'string' as const, title: 'Label', initialState: '' },
  inputHint: {
    type: 'number' as const,
    title: 'Input Hint',
    initialState: 60,
    help: 'Given in seconds'
  },
  showDay: { type: 'boolean' as const, title: 'Show Days', initialState: true },
  showHour: { type: 'boolean' as const, title: 'Show Hours', initialState: true },
  showMinute: { type: 'boolean' as const, title: 'Show Minutes', initialState: true },
  showSecond: { type: 'boolean' as const, title: 'Show Seconds', initialState: true },
  showMillisecond: { type: 'boolean' as const, title: 'Show Milliseconds', initialState: false }
} satisfies PanelConfigFor<typeof CmkTimeSpan, OmittedProps> & AdditionalProps
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { computed, ref } from 'vue'

import CmkTimeSpan from '@/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'
import { type Magnitude } from '@/components/user-input/CmkTimeSpan/timeSpan'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkTimeSpan, OmittedProps>().createRef(panelConfig)
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
        v-model="data"
        :label="propState.label"
        title="Duration"
        :input-hint="propState.inputHint"
        :displayed-magnitudes="displayedMagnitudes"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
