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
import { renderTimeOfDay } from 'cmk-ui-library/lib/renderTime'
import { computed, nextTick, ref, watch } from 'vue'

import { useGlobalRefresh } from '../GlobalTimePicker/globalTimeState'

const { lastRefreshPosition, intervalChoicesSeconds } = defineProps<{
  lastRefreshPosition: 'top' | 'left'
  intervalChoicesSeconds: number[]
}>()

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

const TURN_OFF = 'turn-off'

const intervalOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: [
    ...[...new Set([...intervalChoicesSeconds, refreshIntervalSeconds.value])]
      .sort((secondsA, secondsB) => secondsA - secondsB)
      .map((seconds) => ({ name: String(seconds), title: _t('%{seconds} sec', { seconds }) })),
    { name: TURN_OFF, title: _t('Turn off') }
  ]
}))

// Each control unmounts itself when used, so the one taking its place takes the focus and its name
// announces the new state.
const intervalDropdown = ref<InstanceType<typeof CmkDropdown> | null>(null)
const resumeButton = ref<InstanceType<typeof CmkButton> | null>(null)

const intervalModel = computed<string | null>({
  get: () => String(refreshIntervalSeconds.value),
  set: (value) => {
    if (value === TURN_OFF) {
      pauseRefresh()
      void nextTick(() => resumeButton.value?.focus())
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
  void nextTick(() => intervalDropdown.value?.focus())
}

const lastRefreshLabel = computed(() => {
  const time = lastRefreshAt.value
  if (time === null) {
    return null
  }
  return renderTimeOfDay(time)
})
</script>

<template>
  <div
    class="graphing-global-refresh-control"
    :class="{
      'graphing-global-refresh-control--last-refresh-top': lastRefreshPosition === 'top',
      'graphing-global-refresh-control--last-refresh-left': lastRefreshPosition === 'left'
    }"
  >
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
        <span class="graphing-global-refresh-control__title" aria-hidden="true">
          {{ _t('Live refresh') }}
        </span>
        <span aria-hidden="true">{{ _t('every') }}</span>
        <CmkDropdown
          ref="intervalDropdown"
          v-model="intervalModel"
          :options="intervalOptions"
          :label="_t('Live refresh every')"
          required
        />
      </template>
      <template v-else>
        <span class="graphing-global-refresh-control__title">{{ _t('Refresh off') }}</span>
        <CmkButton
          ref="resumeButton"
          size="small"
          class="graphing-global-refresh-control__resume"
          :aria-label="_t('Resume live refresh')"
          @click="resume"
        >
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
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

.graphing-global-refresh-control--last-refresh-top {
  flex-direction: column;
  align-items: flex-end;
}

.graphing-global-refresh-control--last-refresh-left {
  align-items: center;
  gap: var(--dimension-4);
}

.graphing-global-refresh-control__last-refresh {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* Out of flow: in flow this makes the control taller when the refresh is off, and the host
   centres it in a fixed-height row, so the pill would slide out of line with the picker. */
.graphing-global-refresh-control--last-refresh-top .graphing-global-refresh-control__last-refresh {
  position: absolute;
  right: 0;
  bottom: 100%;
  margin-bottom: var(--dimension-3);
}

.graphing-global-refresh-control__pill {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  border-radius: var(--border-radius);
  background: var(--status-background-success);

  > :deep(.cmk-dropdown) {
    align-self: center;
  }
}

.graphing-global-refresh-control__pill--paused {
  background: var(--status-background-warning);
}

.graphing-global-refresh-control__dot {
  box-sizing: border-box;
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border: var(--border-width-1) solid var(--status-border-color-success-strong);
  border-radius: 50%;
  background: var(--success);
}

.graphing-global-refresh-control__pill--paused .graphing-global-refresh-control__dot {
  border-color: var(--status-border-color-warning-strong);
  background: var(--color-state-warning);
}

.graphing-global-refresh-control__title {
  font-weight: var(--font-weight-bold);
}

.graphing-global-refresh-control__resume {
  margin-left: var(--dimension-3);
  gap: var(--dimension-3);
  font-weight: var(--font-weight-default);
}
</style>
