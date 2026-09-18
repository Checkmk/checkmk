<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import { useGlobalRefresh } from '../GlobalTimePicker/globalTimeState'
import { pad2 } from '../utils/timeFormat'

const {
  refreshIntervalSeconds,
  refreshPaused,
  refreshTick,
  setRefreshIntervalSeconds,
  pauseRefresh,
  resumeRefresh
} = useGlobalRefresh()

const lastRefreshAt = ref<Date | null>(null)

watch(refreshTick, () => {
  lastRefreshAt.value = new Date()
})

const { _t } = usei18n()

// Kept in sync by hand with GRAPH_REFRESH_INTERVALS_SECONDS, which backs the profile setting
// preselecting one of these.
const INTERVAL_CHOICES_SECONDS = [30, 60, 90]
const TURN_OFF = 'turn-off'

const intervalOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: [
    ...[...new Set([...INTERVAL_CHOICES_SECONDS, refreshIntervalSeconds.value])]
      .sort((secondsA, secondsB) => secondsA - secondsB)
      .map((seconds) => ({ name: String(seconds), title: _t('%{seconds} sec', { seconds }) })),
    { name: TURN_OFF, title: _t('Turn off') }
  ]
}))

const intervalModel = computed<string | null>({
  get: () => String(refreshIntervalSeconds.value),
  set: (value) => {
    if (value === TURN_OFF) {
      pauseRefresh()
    } else if (value !== null) {
      // Only rendered while the refresh runs, so this only changes the rhythm; Resume goes live.
      setRefreshIntervalSeconds(Number(value))
    }
  }
})

const emit = defineEmits<{ resume: [] }>()

function resume(): void {
  // The range first: the refresh that follows draws whatever window this leaves behind.
  emit('resume')
  resumeRefresh()
}

const lastRefreshLabel = computed(() => {
  const time = lastRefreshAt.value
  if (time === null) {
    return null
  }
  return `${pad2(time.getHours())}:${pad2(time.getMinutes())}:${pad2(time.getSeconds())}`
})
</script>

<template>
  <div class="graphing-global-refresh-control">
    <span
      v-if="refreshPaused && lastRefreshLabel"
      class="graphing-global-refresh-control__last-refresh"
    >
      {{ _t('Last refresh: %{time}', { time: lastRefreshLabel }) }}
    </span>
    <div
      class="graphing-global-refresh-control__pill"
      :class="{ 'graphing-global-refresh-control__pill--paused': refreshPaused }"
    >
      <span class="graphing-global-refresh-control__dot" aria-hidden="true" />
      <template v-if="!refreshPaused">
        <span class="graphing-global-refresh-control__title">{{ _t('Live refresh') }}</span>
        <span>{{ _t('every') }}</span>
        <CmkDropdown
          v-model="intervalModel"
          :options="intervalOptions"
          :label="_t('Refresh interval')"
          required
        />
      </template>
      <template v-else>
        <span class="graphing-global-refresh-control__title">{{ _t('Refresh off') }}</span>
        <CmkButton size="small" class="graphing-global-refresh-control__resume" @click="resume">
          <CmkMultitoneIcon name="play" primary-color="success" size="small" />
          {{ _t('Resume') }}
        </CmkButton>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.graphing-global-refresh-control {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

/* Out of flow: in flow this makes the control taller when the refresh is off, and the host
   centres it in a fixed-height row, so the pill would slide out of line with the picker. */
.graphing-global-refresh-control__last-refresh {
  position: absolute;
  right: 0;
  bottom: 100%;
  margin-bottom: var(--dimension-3);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.graphing-global-refresh-control__pill {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  border-radius: var(--border-radius);
  background: var(--graphing-refresh-live-bg);

  > :deep(.cmk-dropdown) {
    align-self: center;
  }
}

.graphing-global-refresh-control__pill--paused {
  background: var(--graphing-refresh-off-bg);
}

.graphing-global-refresh-control__dot {
  box-sizing: border-box;
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border: var(--border-width-1) solid var(--graphing-refresh-live-dot-stroke);
  border-radius: 50%;
  background: var(--color-corporate-green-50);
}

.graphing-global-refresh-control__pill--paused .graphing-global-refresh-control__dot {
  border-color: var(--graphing-refresh-off-dot-stroke);
  background: var(--color-yellow-50);
}

body[data-theme='facelift'] {
  .graphing-global-refresh-control {
    --graphing-refresh-live-bg: var(--color-corporate-green-0);
    --graphing-refresh-off-bg: var(--color-yellow-0);
    --graphing-refresh-live-dot-stroke: var(--color-corporate-green-70);
    --graphing-refresh-off-dot-stroke: var(--color-yellow-70);
  }
}

body[data-theme='modern-dark'] {
  .graphing-global-refresh-control {
    --graphing-refresh-live-bg: var(--color-corporate-green-100);
    --graphing-refresh-off-bg: var(--color-yellow-100);

    /* Same colour as the fill: dark mode shows no ring, but the border keeps the dot 8x8. */
    --graphing-refresh-live-dot-stroke: var(--color-corporate-green-50);
    --graphing-refresh-off-dot-stroke: var(--color-yellow-50);
  }
}

.graphing-global-refresh-control__title {
  font-weight: var(--font-weight-bold);
}

.graphing-global-refresh-control__resume {
  margin-left: var(--dimension-3);
  gap: var(--dimension-3);
}
</style>
