<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CalendarDate } from '@internationalized/date'
import { computed, useTemplateRef } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { TriggerAria } from '@/components/CmkFlyout'

import type { DateFormatParts, DateTimePartsDraft, HourCycle, TimeValue } from '../../types'
import FieldBox from './FieldBox.vue'
import SegmentedField from './SegmentedField.vue'
import { useDateField } from './useDateField'
import { useSegmentedField } from './useSegmentedField'
import { useTimeField } from './useTimeField'

const props = withDefaults(
  defineProps<{
    /** Resolved date section order/separator (e.g. `settings.dateFormat` from the resolver). */
    dateFormat: DateFormatParts
    /** Full month names (index 0 = January) for the month segment's spoken value. */
    monthNames: TranslatedString[]
    /** Resolved 12h/24h display cycle (e.g. `settings.hourCycle` from the resolver). */
    hourCycle: HourCycle
    /** Show the leading calendar icon. Fields inside a flyout render without icons. */
    showIcon?: boolean
    /** Render the field non-interactive and dimmed. */
    disabled?: boolean
    /** Accessible name for the date field; defaults to "Date". */
    dateAriaLabel?: TranslatedString | undefined
    /** Accessible name for the time field; defaults to "Time". */
    timeAriaLabel?: TranslatedString | undefined
    /** Merge the field box into the popup opening below it (see FieldBox). */
    open?: boolean
    /** Act as the flyout trigger: the icon becomes an "Open calendar" button and clicking into
     *  the field opens the popup. Off for fields inside an already-open flyout (e.g. the range
     *  picker rows). */
    asTrigger?: boolean
    /** ARIA wiring from the flyout, placed on the icon trigger button (see FieldBox). */
    triggerAria?: TriggerAria | undefined
  }>(),
  { showIcon: true }
)

/** The edited date + time draft. The object is always present; each half is `null` while empty. */
const model = defineModel<DateTimePartsDraft>({ required: true })

const emit = defineEmits<{
  /** The user requested commit (Enter in a cell). */
  (e: 'commit'): void
  /** The user requested the popup open (click) — only emitted in trigger mode. */
  (e: 'open'): void
  /** The user toggled the popup via the icon button — only emitted in trigger mode. */
  (e: 'toggle'): void
}>()

const { _t } = usei18n()

// Two writable views over the single model, one per engine.
const dateView = computed<CalendarDate | null>({
  get: () => model.value.date,
  set: (date) => {
    model.value = { ...model.value, date }
  }
})
const timeView = computed<TimeValue | null>({
  get: () => model.value.time,
  set: (time) => {
    model.value = { ...model.value, time }
  }
})

// Arrow stepping the time across midnight carries into the date (no-op while the date is empty).
function carryDays(days: -1 | 1): void {
  if (model.value.date !== null) {
    model.value = { ...model.value, date: model.value.date.add({ days }) }
  }
}

// Relay arrow navigation across the date ↔ time boundary; at the outer edges focus stays put.
const dateApi = useSegmentedField(
  useDateField(
    () => props.dateFormat,
    () => props.monthNames
  ),
  dateView,
  {
    commit: () => emit('commit'),
    navigateOut: (direction) => {
      if (direction === 1) {
        timeApi.focus()
      }
    }
  }
)
const timeApi = useSegmentedField(
  useTimeField(() => props.hourCycle),
  timeView,
  {
    commit: () => emit('commit'),
    navigateOut: (direction) => {
      if (direction === -1) {
        dateApi.focusLast()
      }
    },
    carry: carryDays
  }
)

const fieldBoxRef = useTemplateRef<InstanceType<typeof FieldBox>>('fieldBoxRef')

/** Focus the icon trigger button so the flyout can restore focus on close (see `CmkFlyout`'s
 *  `restoreFocus`). No-op unless the icon trigger button is rendered. */
defineExpose({ focusTriggerButton: () => fieldBoxRef.value?.focusTriggerButton() })
</script>

<template>
  <FieldBox
    ref="fieldBoxRef"
    :icon="props.showIcon ? 'user-interface' : undefined"
    :disabled="props.disabled"
    :open="props.open"
    :as-trigger="props.asTrigger"
    :trigger-aria="props.triggerAria"
    :icon-label="_t('Open calendar')"
    @open="emit('open')"
    @toggle="emit('toggle')"
  >
    <SegmentedField
      :api="dateApi"
      :disabled="props.disabled"
      :aria-label="props.dateAriaLabel ?? _t('Date')"
    />
    <span class="cmk-date-time-input__divider" aria-hidden="true">{{ untranslated('|') }}</span>
    <SegmentedField
      :api="timeApi"
      :disabled="props.disabled"
      :aria-label="props.timeAriaLabel ?? _t('Time')"
    />
  </FieldBox>
</template>

<style scoped>
.cmk-date-time-input__divider {
  padding: 0 var(--dimension-2);
  color: var(--font-color-dimmed);
}
</style>
