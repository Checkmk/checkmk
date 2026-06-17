<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import { computed } from 'vue'

import type { DateTimeRange } from '@/components/date-time'

import GlobalTimePicker from './GlobalTimePicker.vue'
import { rollingRange } from './private/timeRange.ts'
import { useGlobalTimeRange } from './useGlobalTimeRange.ts'

const props = defineProps<GlobalTimePickerProps>()

const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()

const fallback = rollingRange(props.default_time_range)

if (activeTimeRange.value === null) {
  setActiveTimeRange(fallback)
}

const range = computed<DateTimeRange>({
  get: () => activeTimeRange.value ?? fallback,
  set: setActiveTimeRange
})
</script>

<template>
  <GlobalTimePicker
    v-model="range"
    :custom-time-ranges="props.custom_time_ranges"
    :server-time-zone="props.server_time_zone"
  />
</template>
