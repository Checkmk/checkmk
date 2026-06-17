<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { getLocalTimeZone, now } from '@internationalized/date'
import { shallowRef } from 'vue'

import CmkLabel from '@/components/CmkLabel.vue'
import { CmkDateTimePicker, type DateTimePickerSettings } from '@/components/date-time'

const value = shallowRef(now(getLocalTimeZone()))

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
  <CmkDateTimePicker v-model="value" :settings="settings" save-mode :save-handler="onSave">
    <template #save>
      <CmkLabel>Custom save content goes here.</CmkLabel>
    </template>
  </CmkDateTimePicker>
</template>
