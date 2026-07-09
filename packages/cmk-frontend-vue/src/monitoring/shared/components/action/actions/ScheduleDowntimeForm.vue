<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
import { getLocalTimeZone, now } from '@internationalized/date'

import type { DateTimeRange } from '@/components/date-time/types'

export type DurationSelection = 'custom' | 'adhoc' | '4h' | '24h' | '10d'

/** Raw form state. The action turns this into the downtime request body at submit time. */
export interface ScheduleDowntimeFormValues {
  comment: string
  selection: DurationSelection
  customRange: DateTimeRange
  adhocHours: number | undefined
  adhocMinutes: number | undefined
  flexible: boolean
  includeChildHosts: boolean
}

const PRESET_MINUTES: Record<'4h' | '24h' | '10d', number> = {
  '4h': 4 * 60,
  '24h': 24 * 60,
  '10d': 10 * 24 * 60
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
    includeChildHosts: false
  }
}

export function adhocMinutesTotal(values: ScheduleDowntimeFormValues): number {
  return (values.adhocHours ?? 0) * 60 + (values.adhocMinutes ?? 0)
}

export function isScheduleDowntimeValid(values: ScheduleDowntimeFormValues): boolean {
  const durationValid = values.selection !== 'adhoc' || adhocMinutesTotal(values) > 0
  return values.comment.trim() !== '' && durationValid
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
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkCollapsible from '@/components/CmkCollapsible/CmkCollapsible.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsible/CmkCollapsibleTitle.vue'
import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkTimeRangePicker from '@/components/date-time/CmkTimeRangePicker.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

const model = defineModel<ScheduleDowntimeFormValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

const timeZone = getLocalTimeZone()

const customOpen = ref(false)
const durationOpen = ref(true)
const advancedOpen = ref(false)
const repeat = ref<string | null>('fixed')

const durationChips: { id: DurationSelection; label: TranslatedString }[] = [
  { id: 'custom', label: _t('Custom time range') },
  { id: 'adhoc', label: _t('Ad hoc') },
  { id: '4h', label: _t('4 h') },
  { id: '24h', label: _t('24 h') },
  { id: '10d', label: _t('10 d') }
]

const repeatOptions = {
  type: 'fixed' as const,
  suggestions: [{ name: 'fixed', title: _t('never') }]
}

const presetLabel = computed(
  () => durationChips.find((chip) => chip.id === model.value.selection)?.label ?? ''
)

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
    <p class="monitoring-schedule-downtime-form__intro">
      {{ _t('Scheduled downtimes set the hosts in planned maintenance.') }}<br />
      {{ _t('Alerts and notifications will be paused.') }}
    </p>

    <div class="monitoring-schedule-downtime-form__section">
      <label class="monitoring-schedule-downtime-form__field">
        <span class="monitoring-schedule-downtime-form__label">
          {{ _t('Comment') }}<CmkLabelRequired :show="true" space="before" />
        </span>
        <CmkInput
          v-model="model.comment"
          field-size="LARGE"
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
              field-size="SMALL"
              :unit="_t('hours')"
            />
            <CmkInput
              v-model="model.adhocMinutes"
              type="number"
              field-size="SMALL"
              :unit="_t('minutes')"
            />
          </div>
          <p v-else class="monitoring-schedule-downtime-form__preset-hint">
            {{
              _t('Scheduled downtime has a duration of %{duration} starting now.', {
                duration: presetLabel
              })
            }}
          </p>

          <label class="monitoring-schedule-downtime-form__field">
            <span class="monitoring-schedule-downtime-form__label">{{ _t('Repeat') }}</span>
            <CmkDropdown
              :selected-option="repeat"
              :options="repeatOptions"
              :label="_t('Repeat')"
              @update:selected-option="repeat = $event"
            />
          </label>
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
            v-model="model.includeChildHosts"
            :label="_t('Only for hosts: Set child hosts in downtime.')"
          />
          <CmkCheckbox
            v-model="model.flexible"
            :label="
              _t(
                'Only start downtime if the host goes DOWN/UNREACHABLE during the defined start ' +
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

.monitoring-schedule-downtime-form__intro {
  margin: 0;
  color: var(--font-color-dimmed);
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
