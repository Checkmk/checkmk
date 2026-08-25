<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'

import GlobalRefreshControl from '../GlobalRefreshControl/GlobalRefreshControl.vue'
import GlobalTimePicker from './GlobalTimePicker.vue'
import { initGlobalRefresh } from './globalTimeState.ts'
import { useGlobalTimePickerRange } from './useGlobalTimePickerRange.ts'

const props = defineProps<GlobalTimePickerProps>()

const { range, returnToLiveMonitoring } = useGlobalTimePickerRange(props.default_time_range)

initGlobalRefresh({ intervalSeconds: props.default_refresh_time, live: false })
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
