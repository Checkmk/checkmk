<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { CalendarDate } from '@internationalized/date'
import { shallowRef } from 'vue'

import CmkLabel from '@/components/CmkLabel.vue'
import { CmkDatePicker, type DatePickerSettings } from '@/components/date-time'

const value = shallowRef(new CalendarDate(2026, 3, 20))

const settings: DatePickerSettings = {
  dateFormat: 'iso',
  firstDayOfWeek: 1,
  weekendDays: [0, 6]
}

function onSave(): boolean {
  return true
}
</script>

<template>
  <CmkDatePicker v-model="value" :settings="settings" save-mode :save-handler="onSave">
    <template #save>
      <CmkLabel>Custom save content goes here.</CmkLabel>
    </template>
  </CmkDatePicker>
</template>
