<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'

import GlobalTimePickerApp from '@/graphing/GlobalTimePicker/GlobalTimePickerApp.vue'

const HOUR = 3600
const DAY = 24 * HOUR

const props: GlobalTimePickerProps = {
  custom_time_ranges: [
    { title: 'Last 1 hour', total_seconds: HOUR },
    { title: 'Last 6 hours', total_seconds: 6 * HOUR },
    { title: 'Last 24 hours', total_seconds: 24 * HOUR },
    { title: 'Last 8 days', total_seconds: 8 * DAY },
    { title: 'Last 32 days', total_seconds: 32 * DAY }
  ],
  default_time_range: 4 * HOUR,
  server_time_zone: 'America/Los_Angeles'
}
</script>

<template>
  <GlobalTimePickerApp v-bind="props" />
</template>
