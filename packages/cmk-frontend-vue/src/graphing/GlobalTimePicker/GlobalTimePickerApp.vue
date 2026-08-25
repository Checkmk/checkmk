<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { computed } from 'vue'

import GlobalRefreshControl from '../GlobalRefreshControl/GlobalRefreshControl.vue'
import GlobalTimePicker from './GlobalTimePicker.vue'
import { initGlobalRefresh, useGlobalTimeRange } from './globalTimeState.ts'
import { rollingRange } from './private/timeRange.ts'

const props = defineProps<GlobalTimePickerProps>()

const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()

const fallback = rollingRange(props.default_time_range)

if (activeTimeRange.value === null) {
  setActiveTimeRange(fallback, 'time_picker')
}

initGlobalRefresh({ intervalSeconds: props.default_refresh_time, live: false })

const range = computed<DateTimeRange>({
  get: () => activeTimeRange.value ?? fallback,
  set: (value: DateTimeRange) => setActiveTimeRange(value, 'time_picker')
})

function returnToLiveMonitoring(): void {
  setActiveTimeRange(rollingRange(props.default_time_range), 'time_picker')
}
</script>

<template>
  <GlobalTimePicker
    v-model="range"
    :custom-time-ranges="props.custom_time_ranges"
    :server-time-zone="props.server_time_zone"
    :first-day-of-week="props.first_day_of_week"
  >
    <template #aside>
      <GlobalRefreshControl
        class="graphing-global-time-picker-app__refresh"
        @resume="returnToLiveMonitoring"
      />
    </template>
  </GlobalTimePicker>
</template>

<style scoped>
/* Keeps the pill off the page's right edge; the picker itself has no say in that. */
.graphing-global-time-picker-app__refresh {
  margin-right: var(--dimension-7);
}
</style>
