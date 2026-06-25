<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkProgressCircle, {
  type Colors,
  type Sizes
} from '@/components/progress/CmkProgressCircle.vue'

interface RefreshCountdownProps {
  remaining: number
  interval: number
  paused?: boolean
  manualPaused?: boolean
  size?: Sizes
  color?: Colors
  pauseColor?: Colors
}

const {
  remaining,
  interval,
  paused = false,
  manualPaused = false,
  size = 'medium',
  color = 'success',
  pauseColor = 'font'
} = defineProps<RefreshCountdownProps>()

const emit = defineEmits<{ toggle: [] }>()

const secondsLabel = computed<string>(() => Math.max(0, Math.ceil(remaining)).toString())
const accessibilityLabel = computed<string>(() =>
  paused
    ? 'Refresh paused, click to resume'
    : `Refreshing in ${secondsLabel.value} seconds, click to pause`
)
</script>

<template>
  <button
    type="button"
    class="monitoring-refresh-countdown"
    :class="{ 'monitoring-refresh-countdown--paused': paused }"
    :title="accessibilityLabel"
    :aria-label="accessibilityLabel"
    :aria-pressed="paused"
    @click="emit('toggle')"
  >
    <CmkProgressCircle
      :value="remaining"
      :max="interval"
      :size="size"
      :color="manualPaused ? pauseColor : color"
      :label="false"
      :reverse="true"
      aria-hidden="true"
    />
    <span class="monitoring-refresh-countdown__content" aria-hidden="true">
      <CmkMultitoneIcon v-if="paused" name="play" primary-color="font" size="large" />
      <template v-else>
        <span class="monitoring-refresh-countdown__seconds">{{ secondsLabel }}</span>
        <CmkMultitoneIcon
          class="monitoring-refresh-countdown__pause"
          name="pause"
          primary-color="font"
          size="large"
        />
      </template>
    </span>
  </button>
</template>

<style scoped>
.monitoring-refresh-countdown {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
  cursor: pointer;
}

.monitoring-refresh-countdown--paused {
  opacity: 0.6;
}

.monitoring-refresh-countdown__content {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.monitoring-refresh-countdown__seconds {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.monitoring-refresh-countdown__pause {
  display: none;
}

.monitoring-refresh-countdown:hover:not(.monitoring-refresh-countdown--paused)
  .monitoring-refresh-countdown__seconds {
  display: none;
}

.monitoring-refresh-countdown:hover:not(.monitoring-refresh-countdown--paused)
  .monitoring-refresh-countdown__pause {
  display: inline-flex;
}
</style>
