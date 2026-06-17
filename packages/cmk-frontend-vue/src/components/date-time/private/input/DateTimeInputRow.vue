<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkLabel from '@/components/CmkLabel.vue'

import type {
  DateFormatParts,
  DateTimePartsDraft,
  HourCycle,
  Weekday,
  WeekdayNames
} from '../../types'
import GhostWidth from '../display/GhostWidth.vue'
import DateTimeInput from './DateTimeInput.vue'

const props = withDefaults(
  defineProps<{
    /** Leading row label (e.g. "From" / "To"). */
    label: TranslatedString
    /** Resolved date section order/separator (e.g. `settings.dateFormat` from the resolver). */
    dateFormat: DateFormatParts
    /** Full month names (index 0 = January) for the month segment's spoken value. */
    monthNames: TranslatedString[]
    /** Resolved 12h/24h display cycle (e.g. `settings.hourCycle` from the resolver). */
    hourCycle: HourCycle
    /** Short weekday names shown beside the field (e.g. `settings.weekdayNamesShort`). */
    weekdayNames: WeekdayNames
    /** Show the leading calendar icon. Fields inside a flyout render without icons. */
    showIcon?: boolean
    /** Render the field non-interactive and dimmed. */
    disabled?: boolean
    /** Accessible name for the date field; defaults to "Date". */
    dateAriaLabel?: TranslatedString | undefined
    /** Accessible name for the time field; defaults to "Time". */
    timeAriaLabel?: TranslatedString | undefined
  }>(),
  { showIcon: true }
)

/** The endpoint's staged wall-clock draft. Forwarded as-is to the inner {@link DateTimeInput}. */
const model = defineModel<DateTimePartsDraft>({ required: true })

const emit = defineEmits<{
  /** The user requested commit (Enter in a segment). */
  (e: 'commit'): void
}>()

/** The model date's weekday (0=Sunday … 6=Saturday), or `null` when no date is set. */
const weekday = computed<Weekday | null>(() => {
  const { date } = model.value
  if (date === null) {
    return null
  }
  // A calendar date's weekday is timezone-free; create and read the instant in the same fixed
  // zone (UTC) so it never shifts.
  return date.toDate('UTC').getUTCDay() as Weekday
})

const weekdayDisplay = computed<TranslatedString>(() =>
  weekday.value === null ? untranslated('') : props.weekdayNames[weekday.value]
)
</script>

<template>
  <div class="cmk-date-time-input-row">
    <CmkLabel aria-hidden="true">{{ props.label }}</CmkLabel>
    <GhostWidth
      :variants="Object.values(props.weekdayNames)"
      class="cmk-date-time-input-row__weekday"
    >
      <span aria-hidden="true">{{ weekdayDisplay }}</span>
    </GhostWidth>
    <DateTimeInput
      v-model="model"
      :date-format="props.dateFormat"
      :month-names="props.monthNames"
      :hour-cycle="props.hourCycle"
      :show-icon="props.showIcon"
      :disabled="props.disabled"
      :date-aria-label="props.dateAriaLabel"
      :time-aria-label="props.timeAriaLabel"
      @commit="emit('commit')"
    />
  </div>
</template>

<style scoped>
.cmk-date-time-input-row {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
}

.cmk-date-time-input-row__weekday {
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
}
</style>
