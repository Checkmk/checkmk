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
import { computed, ref } from 'vue'

import type { BurgerMenuCallable, BurgerMenuGroup, TimeRange } from '../../types.ts'
import { isoDate, stepLabel } from '../../utils/timeFormat'
import GraphBurgerMenu from '../GraphBurgerMenu.vue'
import type { ZoomMode } from '../TimeSeriesGraph'
import {
  CONSOLIDATION_FUNCTIONS,
  type ConsolidationFn,
  DEFAULT_CONSOLIDATION_FN,
  isConsolidationFn,
  useConsolidationFunctionLabels
} from '../consolidation'
import GraphTitle from './GraphTitle.vue'
import { useHeaderLineBreakLevel } from './useHeaderLineBreakLevel'

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

const consolidationFn = defineModel<ConsolidationFn>('consolidationFn', {
  default: DEFAULT_CONSOLIDATION_FN
})
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

// The header renders title, values-and-time and zoom-and-menu as three atomic blocks; useHeaderLineBreakLevel
// resolves how they flow onto rows as it resizes.
const headerEl = ref<HTMLElement | null>(null)
const titleComp = ref<InstanceType<typeof GraphTitle> | null>(null)
const titleEl = computed<HTMLElement | null>(() => (titleComp.value?.$el as HTMLElement) ?? null)
const valuesAndTimeEl = ref<HTMLElement | null>(null)
const zoomAndMenuEl = ref<HTMLElement | null>(null)

const RAW_DATA_STEP_SECONDS = 60

const dataIsAggregated = computed(
  () => !!props.timeRange && props.timeRange.step > RAW_DATA_STEP_SECONDS
)
const showConsolidationControl = computed(() => !!props.showConsolidation && dataIsAggregated.value)

const showValuesAndTime = computed(
  () => showConsolidationControl.value || (!!props.showTimestamp && !!props.timeRange)
)
const showZoomAndMenu = computed(() => props.showControls || !!props.showBurgerMenu)

const { headerLineBreakLevel } = useHeaderLineBreakLevel(
  {
    headerRef: headerEl,
    titleRef: titleEl,
    valuesAndTimeRef: valuesAndTimeEl,
    zoomAndMenuRef: zoomAndMenuEl
  },
  {
    showTitle: () => !!props.showTitle,
    showValuesAndTime: () => showValuesAndTime.value,
    showZoomAndMenu: () => showZoomAndMenu.value
  }
)

const resolutionLabel = computed(() => {
  const prefix = !!props.isCompact || headerLineBreakLevel.value > 1 ? '@' : _t('resolution:')
  const resolution = props.timeRange ? withMinutesSpelledOut(stepLabel(props.timeRange.step)) : ''
  return `${prefix} ${resolution}`
})
</script>

<template>
  <div
    ref="headerEl"
    class="graphing-graph-header"
    :class="{
      'graphing-graph-header--compact': !!isCompact,
      'graphing-graph-header--title-wrapped': headerLineBreakLevel === 2
    }"
  >
    <GraphTitle
      v-if="showTitle"
      ref="titleComp"
      :title="title ?? ''"
      :is-compact="!!isCompact"
      class="graphing-graph-header__title"
    />
    <div
      v-if="showValuesAndTime"
      ref="valuesAndTimeEl"
      class="graphing-graph-header__values-and-time"
      :class="{ 'graphing-graph-header__values-and-time--second-row': headerLineBreakLevel >= 1 }"
      role="group"
      :aria-label="_t('Graph values and time information')"
    >
      <template v-if="showConsolidationControl">
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
          {{ resolutionLabel }}
        </span>
      </span>
    </div>
    <div
      v-if="showZoomAndMenu"
      ref="zoomAndMenuEl"
      class="graphing-graph-header__zoom-and-menu"
      role="group"
      :aria-label="_t('Graph zoom controls and action menu')"
    >
      <CmkLabeledSwitch
        v-if="showControls"
        v-model="peakZoomActive"
        :off-label="_t('X-zoom')"
        :on-label="_t('Y-zoom')"
        :off-help="_t('Drag to zoom into a time range.')"
        :on-help="_t('Drag to zoom into a value range.')"
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
  --graphing-graph-header-gap: var(--spacing-double);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  column-gap: var(--graphing-graph-header-gap);
  row-gap: var(--dimension-6);
  padding: var(--dimension-4) var(--spacing-double);
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
}

.graphing-graph-header__title {
  flex: 0 0 auto;
  order: 0;
  // with the parent's gap the effective margin-right of the title resolve to --dimension-8 (24px)
  margin-right: calc(var(--dimension-8) - var(--graphing-graph-header-gap));
}

.graphing-graph-header__values-and-time,
.graphing-graph-header__zoom-and-menu {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--dimension-6);
  order: 0;

  > :deep(.cmk-dropdown) {
    align-self: center;
  }
}

.graphing-graph-header__values-and-time {
  margin-left: auto;
  gap: var(--dimension-4);
}

.graphing-graph-header__values-and-time--second-row {
  order: 1;
  margin-left: 0;
}

.graphing-graph-header--title-wrapped .graphing-graph-header__title {
  flex: 1 1 0;
  min-width: 0;
  overflow-wrap: anywhere;
}

// Keep values-and-time on its own row at level 2 - the zero-basis title above would otherwise leave
// room for it to slot back beside the actions on row 1.
.graphing-graph-header--title-wrapped .graphing-graph-header__values-and-time {
  flex-basis: 100%;
}

.graphing-graph-header--title-wrapped .graphing-graph-header__zoom-and-menu {
  align-self: flex-start;
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
