<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkDateTimePickerCodeExample.vue?raw'

type Mode = 'datetime' | 'date' | 'time'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves focus between date segments, time inputs, and trigger buttons.'
  },
  {
    keys: ['ArrowUp', 'ArrowDown'],
    description: 'Increments or decrements the focused date segment or time value.'
  },
  {
    keys: ['ArrowLeft', 'ArrowRight'],
    description: 'Moves focus between date segments or between hours and minutes.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the calendar or time picker popup trigger.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the calendar or time picker popup.'
  }
]

export const panelConfig = {
  mode: {
    type: 'list' as const,
    title: 'Mode',
    options: [
      { title: 'DateTime', name: 'datetime' },
      { title: 'Date', name: 'date' },
      { title: 'Time', name: 'time' }
    ] satisfies Options<Mode>[],
    initialState: 'datetime' as Mode
  },
  suffix: {
    type: 'string' as const,
    title: 'Suffix',
    initialState: 'UTC+1'
  }
} satisfies PanelConfigFor<typeof CmkDateTimePicker, 'date' | 'time'>
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
import { ref } from 'vue'

import CmkDateTimePicker from '@/components/CmkDateTimePicker/CmkDateTimePicker.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
const date = ref('2026-03-15')
const time = ref('14:30')
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDateTimePicker</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkDateTimePicker
        v-model:date="date"
        v-model:time="time"
        :mode="propState.mode"
        :suffix="propState.suffix"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
