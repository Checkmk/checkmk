<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
import { type ZonedDateTime, getLocalTimeZone, now } from '@internationalized/date'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time/types'

import type { DowntimeRecur } from '@/monitoring/shared/api/actions/downtime'

/** An interval the downtime may repeat on, as the page was told its site offers. */
export interface DowntimeRecurrenceOption {
  recur: string
  title: string
}

export type DurationPreset = '4h' | '24h' | '10d'

/** Presets that run until the end of a calendar period rather than for a fixed duration. */
export type UntilPreset = 'today' | 'week' | 'month' | 'year'

export type DurationSelection = 'custom' | 'adhoc' | DurationPreset | UntilPreset

/** Raw form state. The action turns this into the downtime request body at submit time. */
export interface ScheduleDowntimeFormValues {
  comment: string
  selection: DurationSelection
  customRange: DateTimeRange
  adhocHours: number | undefined
  adhocMinutes: number | undefined
  flexible: boolean
  includeChildHosts: boolean
  recur: DowntimeRecur
}

const PRESET_MINUTES: Record<DurationPreset, number> = {
  '4h': 4 * 60,
  '24h': 24 * 60,
  '10d': 10 * 24 * 60
}

const MIDNIGHT = { hour: 0, minute: 0, second: 0, millisecond: 0 } as const

const UNTIL_PRESETS: readonly DurationSelection[] = ['today', 'week', 'month', 'year']

export function isUntilPreset(selection: DurationSelection): selection is UntilPreset {
  return UNTIL_PRESETS.includes(selection)
}

/**
 * The end of the calendar period the preset covers, matching the legacy
 * `time_interval_end`: the start of the next day, of the day after the coming
 * Sunday, of the next month, or of the next year.
 */
export function untilPresetEnd(preset: UntilPreset, start: ZonedDateTime): ZonedDateTime {
  switch (preset) {
    case 'today':
      return start.add({ days: 1 }).set(MIDNIGHT)
    case 'week':
      return start.add({ days: 7 - ((start.toDate().getDay() + 6) % 7) }).set(MIDNIGHT)
    case 'month':
      return start.add({ months: 1 }).set({ day: 1, ...MIDNIGHT })
    case 'year':
      return start.add({ years: 1 }).set({ month: 1, day: 1, ...MIDNIGHT })
  }
}

export function defaultScheduleDowntimeValues(): ScheduleDowntimeFormValues {
  const start = now(getLocalTimeZone())
  return {
    comment: '',
    selection: '4h',
    customRange: { from: start, to: start.add({ hours: 4 }) },
    adhocHours: 2,
    adhocMinutes: 30,
    flexible: false,
    includeChildHosts: false,
    recur: 'fixed'
  }
}

export function adhocMinutesTotal(values: ScheduleDowntimeFormValues): number {
  return (values.adhocHours ?? 0) * 60 + (values.adhocMinutes ?? 0)
}

export function isScheduleDowntimeValid(values: ScheduleDowntimeFormValues): boolean {
  const durationValid = values.selection !== 'adhoc' || adhocMinutesTotal(values) > 0
  return values.comment.trim() !== '' && durationValid && repeatsOnADayEveryMonthHas(values)
}

/**
 * A downtime repeating on the same day of each month can only start on a day that every month
 * has, or the months short of it would go without.
 */
export function repeatsOnADayEveryMonthHas(values: ScheduleDowntimeFormValues): boolean {
  if (values.recur !== 'day_of_month') {
    return true
  }
  const window = downtimeWindow(values)
  return window === null || new Date(window.start).getDate() <= 28
}

/** The absolute downtime window in ISO 8601, or `null` when the selected duration is empty. */
export function downtimeWindow(
  values: ScheduleDowntimeFormValues
): { start: string; end: string } | null {
  if (values.selection === 'custom') {
    return {
      start: values.customRange.from.toDate().toISOString(),
      end: values.customRange.to.toDate().toISOString()
    }
  }
  if (isUntilPreset(values.selection)) {
    const start = now(getLocalTimeZone())
    return {
      start: start.toDate().toISOString(),
      end: untilPresetEnd(values.selection, start).toDate().toISOString()
    }
  }
  const minutes =
    values.selection === 'adhoc' ? adhocMinutesTotal(values) : PRESET_MINUTES[values.selection]
  if (minutes <= 0) {
    return null
  }
  const startDate = new Date()
  return {
    start: startDate.toISOString(),
    end: new Date(startDate.getTime() + minutes * 60_000).toISOString()
  }
}
</script>

<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkCollapsible from 'cmk-ui-library/components/CmkCollapsible/CmkCollapsible.vue'
import CmkCollapsibleTitle from 'cmk-ui-library/components/CmkCollapsible/CmkCollapsibleTitle.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkTimeRangePicker from 'cmk-ui-library/components/date-time/CmkTimeRangePicker.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import type { ActionTargetKind } from '../types'

const props = withDefaults(
  defineProps<{
    targetKind?: ActionTargetKind
    recurrences?: DowntimeRecurrenceOption[]
    /** Where the duration presets are edited. */
    presetsUrl?: string | null
  }>(),
  {
    targetKind: 'host',
    recurrences: () => [],
    presetsUrl: null
  }
)

const model = defineModel<ScheduleDowntimeFormValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

const timeZone = getLocalTimeZone()

const customOpen = ref(false)
const durationOpen = ref(true)
const advancedOpen = ref(false)

const durationChips: {
  id: DurationSelection
  label: TranslatedString
  duration?: TranslatedString
}[] = [
  { id: 'custom', label: _t('Custom time range') },
  { id: 'adhoc', label: _t('Now') },
  { id: '4h', label: _t('4 h'), duration: _t('4 hours') },
  { id: '24h', label: _t('24 h'), duration: _t('24 hours') },
  { id: '10d', label: _t('10 d'), duration: _t('10 days') },
  { id: 'today', label: _t('Today') },
  { id: 'week', label: _t('This week') },
  { id: 'month', label: _t('This month') },
  { id: 'year', label: _t('This year') }
]

const repeatOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: (props.recurrences.length > 0
    ? props.recurrences
    : [{ recur: 'fixed', title: _t('never') }]
  ).map(({ recur, title }) => ({ name: recur, title: title as TranslatedString }))
}))

const monthDayHint = computed(() =>
  repeatsOnADayEveryMonthHas(model.value)
    ? null
    : _t('A downtime repeating monthly has to start between the 1st and the 28th.')
)

const repeat = computed({
  get: () => model.value.recur,
  set: (recur) => {
    model.value.recur = (recur ?? 'fixed') as DowntimeRecur
  }
})

const presetDuration = computed(
  () => durationChips.find((chip) => chip.id === model.value.selection)?.duration ?? ''
)

const untilEndDate = computed(() => {
  const selection = model.value.selection
  if (!isUntilPreset(selection)) {
    return null
  }
  return untilPresetEnd(selection, now(timeZone)).toDate().toLocaleDateString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
})

watch(model, (values) => emit('update:valid', isScheduleDowntimeValid(values)), {
  immediate: true,
  deep: true
})

function selectDuration(id: DurationSelection): void {
  model.value.selection = id
  if (id === 'custom') {
    customOpen.value = true
  }
}
</script>

<template>
  <div class="monitoring-schedule-downtime-form">
    <div class="monitoring-schedule-downtime-form__section">
      <label class="monitoring-schedule-downtime-form__field">
        <span class="monitoring-schedule-downtime-form__label">
          {{ _t('Comment') }}<CmkLabelRequired :show="true" space="before" />
        </span>
        <CmkInput
          v-model="model.comment"
          field-size="large"
          :placeholder="_t('What is the occasion?')"
        />
      </label>
    </div>

    <section class="monitoring-schedule-downtime-form__section">
      <CmkCollapsibleTitle
        :title="_t('Duration')"
        :open="durationOpen"
        @toggle-open="durationOpen = !durationOpen"
      />
      <CmkCollapsible :open="durationOpen">
        <div class="monitoring-schedule-downtime-form__section-body">
          <span class="monitoring-schedule-downtime-form__label">
            {{ _t('Duration') }}<CmkLabelRequired :show="true" space="before" />
          </span>
          <div class="monitoring-schedule-downtime-form__chips">
            <CmkButton
              v-for="chip in durationChips"
              :key="chip.id"
              size="small"
              :variant="model.selection === chip.id ? 'secondary' : 'optional'"
              @click="selectDuration(chip.id)"
            >
              {{ chip.label }}
            </CmkButton>
            <CmkLink
              v-if="presetsUrl"
              class="monitoring-schedule-downtime-form__presets-link"
              :href="presetsUrl"
              target="_blank"
              rel="noopener"
            >
              {{ _t('(edit presets)') }}
            </CmkLink>
          </div>

          <CmkTimeRangePicker
            v-if="model.selection === 'custom'"
            v-model="model.customRange"
            v-model:open="customOpen"
            :time-zone="timeZone"
            :label="_t('Downtime time range')"
          />
          <div
            v-else-if="model.selection === 'adhoc'"
            class="monitoring-schedule-downtime-form__adhoc"
          >
            <span>{{ _t('From now, for') }}</span>
            <CmkInput
              v-model="model.adhocHours"
              type="number"
              field-size="small"
              :unit="_t('hours')"
            />
            <CmkInput
              v-model="model.adhocMinutes"
              type="number"
              field-size="small"
              :unit="_t('minutes')"
            />
          </div>
          <p v-else-if="untilEndDate" class="monitoring-schedule-downtime-form__preset-hint">
            {{
              _t('Scheduled downtime, starting now and ending on %{date}.', {
                date: untilEndDate
              })
            }}
          </p>
          <p v-else class="monitoring-schedule-downtime-form__preset-hint">
            {{
              _t('Scheduled downtime, starting now with a duration of %{duration}.', {
                duration: presetDuration
              })
            }}
          </p>

          <label class="monitoring-schedule-downtime-form__field">
            <span class="monitoring-schedule-downtime-form__label">{{ _t('Repeat') }}</span>
            <CmkDropdown v-model="repeat" :options="repeatOptions" :label="_t('Repeat')" />
          </label>
          <p v-if="monthDayHint" class="monitoring-schedule-downtime-form__preset-hint">
            {{ monthDayHint }}
          </p>
        </div>
      </CmkCollapsible>
    </section>

    <section class="monitoring-schedule-downtime-form__section">
      <CmkCollapsibleTitle
        :title="_t('Advanced option')"
        :open="advancedOpen"
        @toggle-open="advancedOpen = !advancedOpen"
      />
      <CmkCollapsible :open="advancedOpen">
        <div class="monitoring-schedule-downtime-form__section-body">
          <CmkCheckbox
            v-if="props.targetKind === 'host'"
            v-model="model.includeChildHosts"
            :label="_t('Only for hosts: Set child hosts in downtime.')"
          />
          <CmkCheckbox
            v-model="model.flexible"
            :label="
              _t(
                'Only start downtime if host/service goes DOWN/UNREACH within the defined start ' +
                  'and end time (flexible).'
              )
            "
          />
        </div>
      </CmkCollapsible>
    </section>
  </div>
</template>

<style scoped>
.monitoring-schedule-downtime-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-schedule-downtime-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-schedule-downtime-form__label {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  font-weight: var(--font-weight-bold);
}

.monitoring-schedule-downtime-form__section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--spacing);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
}

.monitoring-schedule-downtime-form__section-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-schedule-downtime-form__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);
}

.monitoring-schedule-downtime-form__presets-link {
  align-self: center;
  width: auto;
}

.monitoring-schedule-downtime-form__adhoc {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3);
}

.monitoring-schedule-downtime-form__preset-hint {
  margin: 0;
  color: var(--font-color-dimmed);
}
</style>
