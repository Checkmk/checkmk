<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T extends TimeRangePresetItem">
import CmkChipSelect from 'cmk-ui-library/components/CmkChipSelect.vue'
import type { Suggestion, Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { usePresetOverflow } from '@/lib/usePresetOverflow'

import TimeRangeChip from './TimeRangeChip.vue'
import type { TimeRangePresetItem } from './types'

const props = withDefaults(
  defineProps<{
    presets: T[]
    selectedName: string | null
    /** `condensed` drops the chips and offers every preset from the dropdown alone. */
    variant?: 'extended' | 'condensed'
  }>(),
  { variant: 'extended' }
)

const emit = defineEmits<{ select: [preset: T] }>()

defineSlots<{
  /** Replaces a live chip, e.g. to wrap it in a tooltip. Must render a `TimeRangeChip`: the
   *  off-screen measure row always uses the default chip, so a wider chip would break the fit. */
  chip?: (props: { preset: T; selected: boolean; select: () => void }) => unknown
  /** Per-option content of the overflow dropdown; defaults to the preset title. */
  option?: (props: { suggestion: Suggestion }) => unknown
  /** Content that always follows the presets; its width is reserved from the row. */
  trailing?: () => unknown
}>()

const { _t } = usei18n()

const rootRef = ref<HTMLElement | null>(null)
const measureRef = ref<HTMLElement | null>(null)
const overflowMeasureRef = ref<HTMLElement | null>(null)
const trailingMeasureRef = ref<HTMLElement | null>(null)

const { visiblePresets, overflowPresets, hasOverflow } = usePresetOverflow(
  { rootRef, measureRef, overflowMeasureRef, trailingMeasureRef },
  () => props.presets
)

// The measure replica only needs the trigger width, so it carries no options.
const EMPTY_OPTIONS: Suggestions = { type: 'fixed', suggestions: [] }

const isCondensed = computed(() => props.variant === 'condensed')
const selectPresets = computed(() => (isCondensed.value ? props.presets : overflowPresets.value))

const overflowOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: selectPresets.value.map((preset) => ({ name: preset.name, title: preset.title }))
}))

const overflowSelectedName = computed(() =>
  selectPresets.value.some((preset) => preset.name === props.selectedName)
    ? props.selectedName
    : null
)

function onOverflowSelect(name: string | null): void {
  const preset = props.presets.find((candidate) => candidate.name === name)
  if (preset) {
    emit('select', preset)
  }
}
</script>

<template>
  <div ref="rootRef" class="lib-time-range-preset-row">
    <!-- Every chip at natural width, off-screen: the fit is measured here, never on the live row,
         so trimming the row cannot feed back into the measurement. -->
    <div
      v-if="!isCondensed"
      class="lib-time-range-preset-row__measure-clip"
      aria-hidden="true"
      inert
    >
      <div ref="measureRef" class="lib-time-range-preset-row__measure">
        <TimeRangeChip v-for="preset in presets" :key="preset.name" :selected="false">
          {{ preset.title }}
        </TimeRangeChip>
        <div ref="overflowMeasureRef">
          <CmkChipSelect
            :model-value="null"
            :options="EMPTY_OPTIONS"
            :label="_t('More time ranges')"
            :input-hint="_t('More ranges')"
            static-label
          />
        </div>
        <div v-if="$slots.trailing" ref="trailingMeasureRef">
          <slot name="trailing" />
        </div>
      </div>
    </div>

    <template v-if="!isCondensed">
      <template v-for="preset in visiblePresets" :key="preset.name">
        <slot
          name="chip"
          :preset="preset"
          :selected="selectedName === preset.name"
          :select="() => emit('select', preset)"
        >
          <TimeRangeChip :selected="selectedName === preset.name" @click="emit('select', preset)">
            {{ preset.title }}
          </TimeRangeChip>
        </slot>
      </template>
    </template>

    <div v-if="isCondensed || hasOverflow" class="lib-time-range-preset-row__overflow">
      <CmkChipSelect
        :model-value="overflowSelectedName"
        :options="overflowOptions"
        :label="isCondensed ? _t('Time ranges') : _t('More time ranges')"
        :input-hint="isCondensed ? _t('Time range') : _t('More ranges')"
        :static-label="!isCondensed"
        @update:model-value="onOverflowSelect"
      >
        <template v-if="$slots.option" #option="slotProps">
          <slot name="option" v-bind="slotProps" />
        </template>
      </CmkChipSelect>
    </div>

    <div v-if="$slots.trailing" class="lib-time-range-preset-row__trailing">
      <slot name="trailing" />
    </div>
  </div>
</template>

<style scoped>
.lib-time-range-preset-row {
  min-width: 0;
  overflow: clip visible;
  overflow-clip-margin: 2px;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: var(--dimension-3);
}

.lib-time-range-preset-row__measure-clip {
  position: absolute;
  width: 0;
  height: 0;
  overflow: clip;
}

.lib-time-range-preset-row__measure {
  display: flex;
  width: max-content;
  gap: var(--dimension-3);
}

.lib-time-range-preset-row__overflow,
.lib-time-range-preset-row__trailing {
  flex: 0 0 auto;
}
</style>
