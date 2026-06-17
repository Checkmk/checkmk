<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { PanelConfig } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkDateTimePickerCodeExample.vue?raw'
import {
  dateFormatKnob,
  disabledKnob,
  firstDayOfWeekKnob,
  hourCycleKnob,
  nullableKnob,
  saveModeKnob,
  weekendDaysKnob
} from './uclKnobs'

export const panelConfig = {
  dateFormat: dateFormatKnob,
  hourCycle: hourCycleKnob,
  firstDayOfWeek: firstDayOfWeekKnob,
  weekendDays: weekendDaysKnob,
  saveMode: saveModeKnob,
  disabled: disabledKnob,
  nullable: nullableKnob
} satisfies PanelConfig
</script>

<script setup lang="ts">
import { type ZonedDateTime, getLocalTimeZone, now } from '@internationalized/date'
import {
  PanelStateCreator,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { UserProps } from '@ucl/_ucl/types/prop-def'
import { computed, shallowRef } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'
import {
  CmkDateTimePicker,
  type DateFormatKind,
  type DateTimePickerSettings
} from '@/components/date-time'

import { resolveFirstDayOfWeek, resolveHourCycleKnob, resolveWeekendDays } from './uclKnobs'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkDateTimePicker,
  keyof UserProps<typeof CmkDateTimePicker>
>().createRef(panelConfig)

const model = shallowRef<ZonedDateTime | null>(now(getLocalTimeZone()))

const settings = computed<DateTimePickerSettings>(() => {
  const hourCycle = resolveHourCycleKnob(propState.value.hourCycle)
  const firstDayOfWeek = resolveFirstDayOfWeek(propState.value.firstDayOfWeek)
  const weekendDays = resolveWeekendDays(propState.value.weekendDays)
  return {
    dateFormat: propState.value.dateFormat as DateFormatKind,
    ...(hourCycle !== undefined ? { hourCycle } : {}),
    ...(firstDayOfWeek !== undefined ? { firstDayOfWeek } : {}),
    ...(weekendDays !== undefined ? { weekendDays } : {})
  }
})

function onSave(): boolean {
  return true
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDateTimePicker</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkDateTimePicker
        :key="propState.nullable ? 'nullable' : 'required'"
        v-model="model"
        :settings="settings"
        :nullable="propState.nullable"
        :disabled="propState.disabled"
        :save-mode="propState.saveMode"
        :save-handler="propState.saveMode ? onSave : undefined"
      >
        <template #save>
          <CmkLabel>{{ untranslated('Custom save content goes here.') }}</CmkLabel>
        </template>
      </CmkDateTimePicker>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>
