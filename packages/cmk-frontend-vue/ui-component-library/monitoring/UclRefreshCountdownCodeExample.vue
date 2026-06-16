<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onUnmounted, ref } from 'vue'

import RefreshCountdown from '@/monitoring/shared/components/RefreshCountdown.vue'

const interval = 30
const remaining = ref(interval)
const paused = ref(false)

const timer = window.setInterval(() => {
  if (paused.value) {
    return
  }
  remaining.value = remaining.value <= 1 ? interval : remaining.value - 1
}, 1000)
onUnmounted(() => window.clearInterval(timer))
</script>

<template>
  <RefreshCountdown
    :remaining="remaining"
    :interval="interval"
    :paused="paused"
    @toggle="paused = !paused"
  />
</template>
