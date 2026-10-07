<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { parseAbsoluteToLocal } from '@internationalized/date'
import { onBeforeUnmount, onMounted } from 'vue'

import { reloadPageContent } from '@/graphing/GlobalRefreshControl/pageContentReload'
import {
  initGlobalRefresh,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'

import { isDashboardTimeRangeMessage } from './lib/dashboardTimeRangeMessage'

initGlobalRefresh({ intervalSeconds: null, live: false, strategy: reloadPageContent })

const { setActiveTimeRange } = useGlobalTimeRange()
const { refreshOnce } = useGlobalRefresh()

let lastTick: number | null = null

function followDashboard(event: MessageEvent): void {
  if (event.source !== window.parent || event.origin !== window.location.origin) {
    return
  }
  if (!isDashboardTimeRangeMessage(event.data)) {
    return
  }
  const { range, tick } = event.data
  setActiveTimeRange(
    { from: parseAbsoluteToLocal(range.start), to: parseAbsoluteToLocal(range.end) },
    'time_picker'
  )
  if (lastTick !== null && tick !== lastTick) {
    refreshOnce()
  }
  lastTick = tick
}

onMounted(() => window.addEventListener('message', followDashboard))
onBeforeUnmount(() => window.removeEventListener('message', followDashboard))
</script>

<template>
  <span hidden />
</template>
