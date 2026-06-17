<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { PanelConfig } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkTimePickerCodeExample.vue?raw'
import { disabledKnob, hourCycleKnob, nullableKnob } from './uclKnobs'

export const panelConfig = {
  hourCycle: hourCycleKnob,
  disabled: disabledKnob,
  nullable: nullableKnob
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { UserProps } from '@ucl/_ucl/types/prop-def'
import { computed, ref } from 'vue'

import { CmkTimePicker, type TimePickerSettings, type TimeValue } from '@/components/date-time'

import { resolveHourCycleKnob } from './uclKnobs'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkTimePicker,
  keyof UserProps<typeof CmkTimePicker>
>().createRef(panelConfig)

const value = ref<TimeValue | null>({ hour: 9, minute: 5 })
const settings = computed<TimePickerSettings>(() => {
  const hourCycle = resolveHourCycleKnob(propState.value.hourCycle)
  return hourCycle !== undefined ? { hourCycle } : {}
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTimePicker</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTimePicker
        :key="propState.nullable ? 'nullable' : 'required'"
        v-model="value"
        :settings="settings"
        :nullable="propState.nullable"
        :disabled="propState.disabled"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>
