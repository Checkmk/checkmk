<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, useTemplateRef } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import { fromMeridiemHour, toMeridiemHour } from '../../dateTimeUtils'
import type { HourCycle, Meridiem, MeridiemCycle, TimeValue } from '../../types'
import TimeSelectorColumn from './TimeSelectorColumn.vue'

const props = defineProps<{
  /** Resolved display cycle; a meridiem cycle (h11/h12) adds the AM/PM column. */
  hourCycle: HourCycle
}>()

const emit = defineEmits<{
  /** The user requested commit (Enter on a column option). */
  (e: 'commit'): void
}>()

/** The selected time. */
const model = defineModel<TimeValue>({ required: true })

const { _t } = usei18n()

const hourColumnRef = useTemplateRef('hourColumnRef')
const minuteColumnRef = useTemplateRef('minuteColumnRef')
const meridiemColumnRef = useTemplateRef('meridiemColumnRef')

// The meridiem cycle (h11/h12) adds the AM/PM column and drives the display conversion; `null` is
// the 24-hour mode, where the hour column is the canonical 0-23 hour.
const meridiemCycle = computed<MeridiemCycle | null>(() =>
  props.hourCycle === 24 ? null : props.hourCycle
)

const hourOptions = computed<number[]>(() => {
  if (meridiemCycle.value === null) {
    return Array.from({ length: 24 }, (_unused, index) => index)
  }
  // h12 shows 1..12, h11 shows 0..11.
  const start = meridiemCycle.value === 11 ? 0 : 1
  return Array.from({ length: 12 }, (_unused, index) => index + start)
})
const minuteOptions = Array.from({ length: 60 }, (_unused, index) => index)
const meridiemOptions: Meridiem[] = ['AM', 'PM']

const hourModel = computed<number>({
  get: () =>
    meridiemCycle.value !== null
      ? toMeridiemHour(model.value.hour, meridiemCycle.value).displayHour
      : model.value.hour,
  set: (option) => {
    model.value = {
      ...model.value,
      hour: meridiemCycle.value !== null ? fromMeridiemHour(option, meridiemModel.value) : option
    }
  }
})

const minuteModel = computed<number>({
  get: () => model.value.minute,
  set: (option) => {
    model.value = { ...model.value, minute: option }
  }
})

const meridiemModel = computed<Meridiem>({
  // The AM/PM marker is cycle-independent (it only depends on hour < 12), so a fallback cycle is
  // safe here; this getter is only read while a meridiem column is shown.
  get: () => toMeridiemHour(model.value.hour, meridiemCycle.value ?? 12).meridiem,
  set: (option) => {
    model.value = { ...model.value, hour: fromMeridiemHour(hourModel.value, option) }
  }
})

function scrollSelectedIntoView(): void {
  hourColumnRef.value?.centerSelected()
  minuteColumnRef.value?.centerSelected()
}

/**
 * Move DOM focus onto the selected hour option. The owner calls this when the selector is opened
 * via an explicit "open" affordance (e.g. the picker's icon button), landing the keyboard user in
 * the wheel; opening by typing in the trigger field deliberately leaves focus in the field.
 */
function focus(): void {
  hourColumnRef.value?.focusSelected()
}

defineExpose({ focus })

function onHourNavigate(direction: 'previous' | 'next'): void {
  if (direction === 'next') {
    minuteColumnRef.value?.focusSelected()
  }
}

function onMinuteNavigate(direction: 'previous' | 'next'): void {
  if (direction === 'previous') {
    hourColumnRef.value?.focusSelected()
  } else if (meridiemCycle.value !== null) {
    meridiemColumnRef.value?.focusSelected()
  }
}

function onMeridiemNavigate(direction: 'previous' | 'next'): void {
  if (direction === 'previous') {
    minuteColumnRef.value?.focusSelected()
  }
}

function pad(value: number, length = 2): string {
  return value.toString().padStart(length, '0')
}

onMounted(scrollSelectedIntoView)
</script>

<template>
  <div class="cmk-time-selector" role="group" :aria-label="_t('Time selection')">
    <TimeSelectorColumn
      ref="hourColumnRef"
      v-model="hourModel"
      :options="hourOptions"
      :label="_t('Hour')"
      :format="pad"
      @navigate="onHourNavigate"
      @commit="emit('commit')"
    />
    <span class="cmk-time-selector__separator" aria-hidden="true">{{ untranslated(':') }}</span>
    <TimeSelectorColumn
      ref="minuteColumnRef"
      v-model="minuteModel"
      :options="minuteOptions"
      :label="_t('Minute')"
      :format="pad"
      @navigate="onMinuteNavigate"
      @commit="emit('commit')"
    />
    <TimeSelectorColumn
      v-if="meridiemCycle !== null"
      ref="meridiemColumnRef"
      v-model="meridiemModel"
      class="cmk-time-selector__meridiem"
      :options="meridiemOptions"
      :label="_t('AM or PM')"
      :format="untranslated"
      @navigate="onMeridiemNavigate"
      @commit="emit('commit')"
    />
    <div v-else class="cmk-time-selector__meridiem" aria-hidden="true"></div>
  </div>
</template>

<style scoped>
.cmk-time-selector {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-3);
  font-variant-numeric: tabular-nums;
}

.cmk-time-selector__meridiem {
  min-width: 36px;
}

.cmk-time-selector__separator {
  align-self: flex-start;
  padding-top: var(--dimension-4);
  color: var(--font-color);
}
</style>
