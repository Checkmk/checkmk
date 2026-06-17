<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import { CmkTimePicker, type TimePickerSettings, type TimeValue } from '@/components/date-time'

const value = ref<TimeValue>({ hour: 9, minute: 5 })

const settings: TimePickerSettings = {
  hourCycle: 24
}
</script>

<template>
  <CmkTimePicker v-model="value" :settings="settings" />
</template>
