<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { getLocalTimeZone } from '@internationalized/date'
import { renderDate } from 'cmk-ui-library/lib/renderTime'
import { computed } from 'vue'

import { shortWeekday, stepLabel } from '../utils/timeFormat'
import type { TimeRange } from './TimeSeriesGraph'

const props = defineProps<{ timeRange: TimeRange }>()

const label = computed(() => {
  const { start, end, step } = props.timeRange
  const tz = getLocalTimeZone()
  const startDate = renderDate(start, tz)
  const endDate = renderDate(end, tz)
  const stepStr = `@ ${stepLabel(step)}`
  if (startDate === endDate) {
    return `${shortWeekday(start, tz)}, ${startDate} ${stepStr}`
  }
  return `${startDate} — ${endDate} ${stepStr}`
})
</script>

<template>
  <div class="graphing-graph-timestamp">{{ label }}</div>
</template>

<style scoped lang="scss">
.graphing-graph-timestamp {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
}
</style>
