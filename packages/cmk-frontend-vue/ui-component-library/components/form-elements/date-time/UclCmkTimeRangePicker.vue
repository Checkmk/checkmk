<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { PanelConfig } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkTimeRangePickerCodeExample.vue?raw'
import {
  dateFormatKnob,
  disabledKnob,
  firstDayOfWeekKnob,
  hourCycleKnob,
  nullableKnob,
  presetsKnob,
  saveModeKnob,
  weekendDaysKnob
} from './uclKnobs'

export const panelConfig = {
  dateFormat: dateFormatKnob,
  hourCycle: hourCycleKnob,
  firstDayOfWeek: firstDayOfWeekKnob,
  weekendDays: weekendDaysKnob,
  presets: presetsKnob,
  saveMode: saveModeKnob,
  disabled: disabledKnob,
  nullable: nullableKnob
} satisfies PanelConfig
</script>

<script setup lang="ts">
import { getLocalTimeZone, now } from '@internationalized/date'
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
  CmkTimeRangePicker,
  type DateFormatKind,
  type DateTimePickerSettings,
  type DateTimeRange,
  type RangePreset
} from '@/components/date-time'

import { resolveFirstDayOfWeek, resolveHourCycleKnob, resolveWeekendDays } from './uclKnobs'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkTimeRangePicker,
  keyof UserProps<typeof CmkTimeRangePicker>
>().createRef(panelConfig)

const range = shallowRef<DateTimeRange | null>({
  from: now(getLocalTimeZone()),
  to: now(getLocalTimeZone()).add({ weeks: 1 })
})

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

const samplePresets: RangePreset[] = [
  {
    id: 'today',
    label: untranslated('Today'),
    getRange: () => {
      const start = now(getLocalTimeZone()).set({
        hour: 0,
        minute: 0,
        second: 0,
        millisecond: 0
      })
      return { from: start, to: start.add({ days: 1 }) }
    }
  },
  {
    id: 'last-7-days',
    label: untranslated('Last 7 days'),
    getRange: () => {
      const end = now(getLocalTimeZone())
      return { from: end.subtract({ days: 7 }), to: end }
    }
  },
  {
    id: 'last-30-days',
    label: untranslated('Last 30 days'),
    getRange: () => {
      const end = now(getLocalTimeZone())
      return { from: end.subtract({ days: 30 }), to: end }
    }
  }
]

function onSave(): boolean {
  return true
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTimeRangePicker</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTimeRangePicker
        :key="propState.nullable ? 'nullable' : 'required'"
        v-model="range"
        :settings="settings"
        :nullable="propState.nullable"
        :disabled="propState.disabled"
        :presets="propState.presets ? samplePresets : undefined"
        :save-mode="propState.saveMode"
        :save-handler="propState.saveMode ? onSave : undefined"
        server-time-zone="America/Los_Angeles"
      >
        <template #save>
          <CmkLabel>{{ untranslated('Custom save content goes here.') }}</CmkLabel>
        </template>
      </CmkTimeRangePicker>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>
