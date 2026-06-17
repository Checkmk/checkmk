<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { getLocalTimeZone, now } from '@internationalized/date'
import { shallowRef } from 'vue'

import CmkLabel from '@/components/CmkLabel.vue'
import {
  CmkTimeRangePicker,
  type DateTimePickerSettings,
  type DateTimeRange
} from '@/components/date-time'

const range = shallowRef<DateTimeRange>({
  from: now(getLocalTimeZone()),
  to: now(getLocalTimeZone()).add({ weeks: 1 })
})

const settings: DateTimePickerSettings = {
  dateFormat: 'iso',
  hourCycle: 24,
  firstDayOfWeek: 1,
  weekendDays: [0, 6]
}

function onSave(): boolean {
  return true
}
</script>

<template>
  <CmkTimeRangePicker
    v-model="range"
    :settings="settings"
    save-mode
    :save-handler="onSave"
    server-time-zone="America/Los_Angeles"
  >
    <template #save>
      <CmkLabel>Custom save content goes here.</CmkLabel>
    </template>
  </CmkTimeRangePicker>
</template>
