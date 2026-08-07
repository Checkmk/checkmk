<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import { type Suggestion } from 'cmk-ui-library/components/CmkSuggestions'
import { fetchRestAPIDeprecated } from 'cmk-ui-library/lib/cmkFetch.ts'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import type { Ref } from 'vue'
import { computed, onMounted, ref, watch } from 'vue'

import DateRangeFields from './DateRangeFields.vue'
import DurationFields from './DurationFields.vue'
import type { PreDefinedTimeRange } from './types'

const { _t } = usei18n()

export interface GraphTimerange {
  type: 'predefined' | 'duration' | 'date' | 'age'
  duration: number | null
  date_range: null | {
    from: string
    to: string
  }
  predefined: PreDefinedTimeRange | null
  age: null | Age
}

export interface Age {
  days: number
  hours: number
  minutes: number
  seconds: number
}

// The keys to predefinedDurationSeconds and predefinedCalendarTitles combined are the complete set
// of `_Predefined` keys from the API. The API's `_Predefined` keys are a mix of trailing durations
// (predefinedDurationSeconds) and calendar-relative ranges (predefinedCalendarTitles).
const predefinedDurationSeconds = {
  last_4_hours: 4 * 60 * 60,
  last_25_hours: 25 * 60 * 60,
  last_8_days: 8 * 24 * 60 * 60,
  last_35_days: 35 * 24 * 60 * 60,
  last_400_days: 400 * 24 * 60 * 60
} as const satisfies Partial<Record<PreDefinedTimeRange, number>>

type PredefinedDurationKey = keyof typeof predefinedDurationSeconds
type PredefinedCalendarKey = Exclude<PreDefinedTimeRange, PredefinedDurationKey>

// Typing this as `Record<PredefinedCalendarKey, ...>` (not `Partial`) makes the two maps a
// compiler-enforced partition of `_Predefined`: together they must cover exactly its keys, with no
// overlap and none missing.
const predefinedCalendarTitles: Record<PredefinedCalendarKey, TranslatedString> = {
  today: _t('Today'),
  yesterday: _t('Yesterday'),
  '7_days_ago': _t('7 days back (this day last week)'),
  '8_days_ago': _t('8 days back'),
  this_week: _t('This week'),
  last_week: _t('Last week'),
  '2_weeks_ago': _t('2 weeks back'),
  this_month: _t('This month'),
  last_month: _t('Last month'),
  this_year: _t('This year'),
  last_year: _t('Last year')
}

const durationOptionName = (totalSeconds: number): string => `duration_${totalSeconds}`

const isDurationPredefinedKey = (key: PreDefinedTimeRange): key is PredefinedDurationKey =>
  key in predefinedDurationSeconds

const secondsToAge = (totalSeconds: number): Age => ({
  days: Math.floor(totalSeconds / 86400),
  hours: Math.floor((totalSeconds % 86400) / 3600),
  minutes: Math.floor((totalSeconds % 3600) / 60),
  seconds: totalSeconds % 60
})

// The trailing-duration length a range denotes - a "last N ..." range stored either as a duration
// or as a trailing-duration predefined key - or null for calendar / custom (age, date) ranges.
const trailingDurationSeconds = (timerange: GraphTimerange): number | null => {
  if (timerange.type === 'duration') {
    return timerange.duration
  }
  if (
    timerange.type === 'predefined' &&
    timerange.predefined !== null &&
    isDurationPredefinedKey(timerange.predefined)
  ) {
    return predefinedDurationSeconds[timerange.predefined]
  }
  return null
}

interface GraphTimerangeApiResult {
  title: string
  extensions: {
    total_seconds: number
  }
}

const selectedTimerange = defineModel<GraphTimerange>('selectedTimerange', { required: true })

const apiDurationTimeranges = ref<GraphTimerangeApiResult[]>([])
const selectedDropdownOption = ref<string | null>(null)

function toPublicTimerange(internal: GraphTimerangeApiResult): GraphTimerange {
  return {
    type: 'duration',
    duration: internal.extensions.total_seconds,
    date_range: null,
    predefined: null,
    age: null
  }
}

const customTimeOptionName = 'custom_time'
const customDateOptionName = 'custom_date'

const customTimeOptionTitle = _t('The last...')
const customDateOptionTitle = _t('Date range')

async function loadApiDurationGraphTimeranges(): Promise<GraphTimerangeApiResult[]> {
  const API_ROOT = 'api/unstable'
  const url = `${API_ROOT}/domain-types/graph_timerange/collections/all`
  const response = await fetchRestAPIDeprecated(url, 'GET')
  await response.raiseForStatus()
  const data = await response.json()
  return data.value
}

const dropdownOptions = computed<Suggestion[]>(() => {
  // The configurable duration ranges are the single source of truth for trailing duration ranges
  // ("last N ...")
  const durationRanges = apiDurationTimeranges.value.map((range) => ({
    name: durationOptionName(range.extensions.total_seconds),
    title: untranslated(range.title)
  }))

  const predefinedRanges = Object.entries(predefinedCalendarTitles).map(([apiKey, title]) => ({
    name: apiKey,
    title
  }))

  const customOptions = [
    { name: customTimeOptionName, title: customTimeOptionTitle },
    { name: customDateOptionName, title: customDateOptionTitle }
  ]

  return [...durationRanges, ...predefinedRanges, ...customOptions]
})

const customDuration: Ref<Age> = ref({
  days: 0,
  hours: 0,
  minutes: 0,
  seconds: 0
})

const customDurationDate = ref({
  from: {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    day: new Date().getDate()
  },
  to: {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    day: new Date().getDate()
  }
})

function getDropdownOptionFromTimerange(timerange: GraphTimerange): string | null {
  switch (timerange.type) {
    case 'duration':
      return timerange.duration === null ? null : durationOptionName(timerange.duration)
    case 'predefined': {
      if (timerange.predefined === null) {
        return null
      }
      // A trailing-duration predefined key resolves to its matching duration option so that it maps
      // onto the same dropdown entry as an equivalent configurable duration range.
      return isDurationPredefinedKey(timerange.predefined)
        ? durationOptionName(predefinedDurationSeconds[timerange.predefined])
        : timerange.predefined
    }
    case 'age':
      return customTimeOptionName
    case 'date':
      return customDateOptionName
  }
}

onMounted(async () => {
  apiDurationTimeranges.value = await loadApiDurationGraphTimeranges()

  if (selectedTimerange.value) {
    const option = getDropdownOptionFromTimerange(selectedTimerange.value)
    const optionAvailable =
      option !== null && dropdownOptions.value.some((suggestion) => suggestion.name === option)
    const fallbackSeconds = optionAvailable
      ? null
      : trailingDurationSeconds(selectedTimerange.value)

    if (fallbackSeconds !== null) {
      // The stored trailing-duration range was edited or removed under Setup > Global settings >
      // Graph time ranges, so it no longer matches a configured option. Fall back to an equivalent
      // custom "The last ..." range instead of rendering a dropdown option 'duration_<n>'.
      customDuration.value = secondsToAge(fallbackSeconds)
      selectedDropdownOption.value = customTimeOptionName
    } else {
      selectedDropdownOption.value = option
    }
    if (selectedTimerange.value.type === 'age' && selectedTimerange.value.age) {
      customDuration.value = { ...selectedTimerange.value.age }
    } else if (selectedTimerange.value.type === 'date' && selectedTimerange.value.date_range) {
      const fromDate = new Date(selectedTimerange.value.date_range.from)
      const toDate = new Date(selectedTimerange.value.date_range.to)
      customDurationDate.value = {
        from: {
          year: fromDate.getFullYear(),
          month: fromDate.getMonth() + 1,
          day: fromDate.getDate()
        },
        to: {
          year: toDate.getFullYear(),
          month: toDate.getMonth() + 1,
          day: toDate.getDate()
        }
      }
    }
  }
})

watch(
  [selectedDropdownOption, customDuration, customDurationDate],
  () => {
    const selectedOption: string = selectedDropdownOption.value ?? ''
    if (selectedOption.startsWith('duration_')) {
      const range = apiDurationTimeranges.value.find(
        (r) => durationOptionName(r.extensions.total_seconds) === selectedOption
      )
      if (range) {
        selectedTimerange.value = toPublicTimerange(range)
      }
    } else if (selectedOption === customTimeOptionName) {
      selectedTimerange.value = {
        type: 'age',
        age: { ...customDuration.value },
        duration: null,
        date_range: null,
        predefined: null
      }
    } else if (selectedOption === customDateOptionName) {
      const getApiDate = (date: { year: number; month: number; day: number }): string => {
        const paddedMonth = String(date.month).padStart(2, '0')
        const paddedDay = String(date.day).padStart(2, '0')
        return `${date.year}-${paddedMonth}-${paddedDay}`
      }

      selectedTimerange.value = {
        type: 'date',
        date_range: {
          from: getApiDate(customDurationDate.value.from),
          to: getApiDate(customDurationDate.value.to)
        },
        duration: null,
        predefined: null,
        age: null
      }
    } else if (selectedOption in predefinedCalendarTitles) {
      // Only calendar-relative predefined ranges reach this branch; trailing durations are stored
      // as duration timeranges above.
      selectedTimerange.value = {
        type: 'predefined',
        predefined: selectedOption as PreDefinedTimeRange,
        duration: null,
        date_range: null,
        age: null
      }
    }
  },
  { deep: true }
)

const isCustomTimeSelected = computed(() => selectedDropdownOption.value === customTimeOptionName)
const isCustomDateSelected = computed(() => selectedDropdownOption.value === customDateOptionName)
</script>

<template>
  <div>
    <CmkDropdown
      v-model="selectedDropdownOption"
      :options="{ type: 'fixed', suggestions: dropdownOptions }"
      :label="_t('Time range')"
    />
    <DurationFields v-if="isCustomTimeSelected" v-model="customDuration" />
    <DateRangeFields v-if="isCustomDateSelected" v-model="customDurationDate" />
  </div>
</template>
