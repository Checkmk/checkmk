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
  initGlobalTime,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import {
  type TimeRangeVariables,
  linkTimeRangeVariables,
  setTimeRangeVariables
} from '@/graphing/GlobalTimePicker/timeRangeUrl'
import { IFRAME_DASHBOARD_URL_PARAM } from '@/page-header/drillUp'

import { isDashboardTimeRangeMessage } from './lib/dashboardTimeRangeMessage'

initGlobalTime({
  intervalSeconds: null,
  start: { type: 'page_default', live: false },
  strategy: reloadPageContent
})

const { setActiveTimeRange } = useGlobalTimeRange()
const { refreshOnce } = useGlobalRefresh()

const LINK_INCLUDING_TIME_RANGE = 'a[data-cmk_includes_time_range]'
const LINK_EVENTS = ['pointerover', 'pointerdown', 'focusin'] as const

let lastTick: number | null = null
let toldTimeRange: TimeRangeVariables | null = null

function followDashboard(event: MessageEvent): void {
  if (event.source !== window.parent || event.origin !== window.location.origin) {
    return
  }
  if (!isDashboardTimeRangeMessage(event.data)) {
    return
  }
  const { range, tick, live } = event.data
  const followed = { from: parseAbsoluteToLocal(range.start), to: parseAbsoluteToLocal(range.end) }
  setActiveTimeRange(followed, 'time_picker')
  if (lastTick !== null && tick !== lastTick) {
    refreshOnce()
  }
  lastTick = tick
  toldTimeRange = linkTimeRangeVariables(followed, live)
  keepWayBackCurrent(toldTimeRange)
}

function keepWayBackCurrent(timeRange: TimeRangeVariables): void {
  const pageUrl = new URL(window.location.href)
  const dashboardUrl = pageUrl.searchParams.get(IFRAME_DASHBOARD_URL_PARAM)
  if (dashboardUrl === null) {
    return
  }
  const wayBack = new URL(dashboardUrl, pageUrl)
  setTimeRangeVariables(wayBack.searchParams, timeRange)
  pageUrl.searchParams.set(IFRAME_DASHBOARD_URL_PARAM, wayBack.toString())
  if (pageUrl.href !== window.location.href) {
    window.history.replaceState(window.history.state, '', pageUrl)
  }
}

function carryTimeRange(event: Event): void {
  if (toldTimeRange === null || !(event.target instanceof Element)) {
    return
  }
  const link = event.target.closest(LINK_INCLUDING_TIME_RANGE)
  if (!(link instanceof HTMLAnchorElement)) {
    return
  }
  const url = new URL(link.href)
  setTimeRangeVariables(url.searchParams, toldTimeRange)
  link.href = url.toString()
}

onMounted(() => {
  window.addEventListener('message', followDashboard)
  for (const type of LINK_EVENTS) {
    document.addEventListener(type, carryTimeRange, true)
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('message', followDashboard)
  for (const type of LINK_EVENTS) {
    document.removeEventListener(type, carryTimeRange, true)
  }
})
</script>

<template>
  <span hidden />
</template>
