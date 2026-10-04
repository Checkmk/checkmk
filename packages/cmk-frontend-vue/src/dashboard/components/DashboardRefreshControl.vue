<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import GlobalRefreshControl from '@/graphing/GlobalRefreshControl/GlobalRefreshControl.vue'
import { useGlobalTimePickerRange } from '@/graphing/GlobalTimePicker/useGlobalTimePickerRange'

const props = defineProps<{
  defaultTimeRange: number
  intervalChoicesSeconds: number[]
}>()

const { returnToLiveMonitoring } = useGlobalTimePickerRange(props.defaultTimeRange)
</script>

<template>
  <!-- Going live means a window ending now: a zoomed one would keep redrawing the same past. -->
  <GlobalRefreshControl
    last-refresh-position="left"
    :interval-choices-seconds="props.intervalChoicesSeconds"
    @resume="returnToLiveMonitoring"
  />
</template>
