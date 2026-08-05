<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { fromAbsolute, getLocalTimeZone } from '@internationalized/date'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkLabeledSwitch from 'cmk-ui-library/components/CmkLabeledSwitch.vue'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { BurgerMenuCallable, BurgerMenuGroup, TimeRange } from '../types.ts'
import { isoDate, stepLabel } from '../utils/timeFormat'
import GraphBurgerMenu from './GraphBurgerMenu.vue'
import GraphTitle from './GraphTitle.vue'
import type { ZoomMode } from './TimeSeriesGraph'
import {
  CONSOLIDATION_FUNCTIONS,
  type ConsolidationFn,
  isConsolidationFn,
  useConsolidationFunctionLabels
} from './consolidation'

// TODO: readjust props to remove the possible omits
const props = withDefaults(
  defineProps<{
    title?: string | undefined
    showTitle?: boolean | undefined
    timeRange?: TimeRange | undefined
    showTimestamp?: boolean | undefined
    showControls?: boolean
    showConsolidation?: boolean | undefined
    showBurgerMenu?: boolean | undefined
    burgerMenuGroups?: BurgerMenuGroup[] | undefined
    isCompact?: boolean | undefined
  }>(),
  { showControls: true }
)

const emit = defineEmits<{ doAction: [onClick: BurgerMenuCallable] }>()

const consolidationFn = defineModel<ConsolidationFn>('consolidationFn', { default: 'avg' })
const zoomMode = defineModel<ZoomMode>('zoomMode', { default: 'time' })

const { _t } = usei18n()

const consolidationFunctionLabels = useConsolidationFunctionLabels()

const consolidationOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: CONSOLIDATION_FUNCTIONS.map((consolidationFunction) => ({
    name: consolidationFunction,
    title: consolidationFunctionLabels.value[consolidationFunction]
  }))
}))

const consolidationModel = computed<string | null>({
  get: () => consolidationFn.value,
  set: (value) => {
    if (isConsolidationFn(value)) {
      consolidationFn.value = value
    }
  }
})

const peakZoomActive = computed({
  get: () => zoomMode.value === 'value',
  set: (active) => {
    zoomMode.value = active ? 'value' : 'time'
  }
})

const dateLabel = computed(() => {
  if (!props.timeRange) {
    return null
  }
  const timeZone = getLocalTimeZone()
  const startDate = isoDate(fromAbsolute(props.timeRange.start * 1000, timeZone))
  const endDate = isoDate(fromAbsolute(props.timeRange.end * 1000, timeZone))
  return startDate === endDate ? startDate : `${startDate} — ${endDate}`
})

function withMinutesSpelledOut(label: string): string {
  return label.replace(/ m$/, ' min')
}

const resolutionLabel = computed(() =>
  props.timeRange ? withMinutesSpelledOut(stepLabel(props.timeRange.step)) : null
)
</script>

<template>
  <div class="graphing-graph-header" :class="{ 'graphing-graph-header--compact': !!isCompact }">
    <GraphTitle v-if="showTitle" :title="title ?? ''" :is-compact="!!isCompact" />
    <div class="graphing-graph-header__controls" role="group" :aria-label="_t('Graph controls')">
      <template v-if="showConsolidation">
        <span class="graphing-graph-header__values-label">{{ _t('Graph values') }}</span>
        <CmkDropdown
          v-model="consolidationModel"
          :options="consolidationOptions"
          :label="_t('Graph values')"
          required
        />
      </template>
      <span v-if="showTimestamp && timeRange" class="graphing-graph-header__timestamp">
        {{ _t('for %{date},', { date: dateLabel ?? '' }) }}
        <span class="graphing-graph-header__resolution">
          {{ _t('resolution: %{resolution}', { resolution: resolutionLabel ?? '' }) }}
        </span>
      </span>
      <CmkLabeledSwitch
        v-if="showControls"
        v-model="peakZoomActive"
        :off-label="_t('Time zoom')"
        :on-label="_t('Peak zoom')"
      />
      <GraphBurgerMenu
        v-if="showBurgerMenu"
        :groups="burgerMenuGroups ?? []"
        :aria-label="_t('Action menu')"
        @do-action="(onClick) => emit('doAction', onClick)"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-double);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
}

.graphing-graph-header__controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-double);
  margin-left: auto;

  > :deep(.cmk-dropdown) {
    align-self: center;
  }
}

.graphing-graph-header__values-label,
.graphing-graph-header__timestamp {
  font-size: var(--font-size-normal);
}

.graphing-graph-header__resolution {
  font-weight: var(--font-weight-bold);
}

.graphing-graph-header--compact .graphing-graph-header__title,
.graphing-graph-header--compact .graphing-graph-header__timestamp {
  font-size: var(--font-size-xsmall);
}
</style>
