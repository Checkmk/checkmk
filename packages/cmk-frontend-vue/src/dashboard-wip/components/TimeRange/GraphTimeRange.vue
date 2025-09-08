<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch.ts'
import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown.vue'
import { type Suggestion } from '@/components/suggestions'

import DateRangeFields from './DateRangeFields.vue'
import DurationFields from './DurationFields.vue'

const { _t } = usei18n()

export interface GraphTimerange {
  type: 'predefined' | 'duration' | 'date' | 'age'
  title: TranslatedString
  duration: number | null
  date_range: null | {
    from: string
    to: string
  }
  predefined: null | string
  age: null | Age
}

export interface Age {
  days: number
  hours: number
  minutes: number
  seconds: number
}

const predefinedTimeranges: Record<string, TranslatedString> = {
  today: _t('Today'),
  yesterday: _t('Yesterday'),
  '7_days_ago': _t('7 days back (this day last week)'),
  this_week: _t('This week'),
  last_week: _t('Last week'),
  '2_weeks_ago': _t('2 weeks back'),
  this_month: _t('This month'),
  last_month: _t('Last month'),
  this_year: _t('This year'),
  last_year: _t('Last year')
}

interface GraphTimerangeApiResult {
  title: string
  extensions: {
    total_seconds: number
  }
}

const selectedTimerange = defineModel<GraphTimerange>('selectedTimerange', { required: true })

const apiDurationTimeranges = ref<GraphTimerange[]>([])
const selectedDropdownOption = ref<string | null>(null)

const customTimeOptionName = 'custom_time'
const customDateOptionName = 'custom_date'

async function loadApiDurationGraphTimeranges(): Promise<GraphTimerange[]> {
  const API_ROOT = 'api/unstable'
  const url = `${API_ROOT}/domain-types/graph_timerange/collections/all`
  const response = await fetchRestAPI(url, 'GET')
  await response.raiseForStatus()
  const data = await response.json()
  const apiTimeranges: GraphTimerange[] = data.value.map((item: GraphTimerangeApiResult) => ({
    type: 'duration',
    title: untranslated(item.title),
    duration: item.extensions.total_seconds,
    date_range: null,
    predefined: null,
    age: null
  }))
  return apiTimeranges
}

onMounted(async () => {
  apiDurationTimeranges.value = await loadApiDurationGraphTimeranges()
})

const dropdownOptions = computed<Suggestion[]>(() => {
  const mappedApiDurationRanges = apiDurationTimeranges.value.map((range) => ({
    name: `duration_${range.duration?.toString() ?? '0'}`,
    title: range.title
  }))

  const mappedPredefinedRanges = Object.entries(predefinedTimeranges).map(([apiKey, title]) => ({
    name: apiKey,
    title: title
  }))

  const customOptions = [
    { name: customTimeOptionName, title: _t('The last...') },
    { name: customDateOptionName, title: _t('Date range') }
  ]

  return [...mappedApiDurationRanges, ...mappedPredefinedRanges, ...customOptions]
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

watch(
  [selectedDropdownOption, customDuration, customDurationDate],
  () => {
    const selectedOption: string = selectedDropdownOption.value ?? ''
    if (selectedOption.startsWith('duration_')) {
      const range = apiDurationTimeranges.value.find(
        (r) => `duration_${r.duration}` === selectedOption
      )
      if (range) {
        selectedTimerange.value = range
      }
    } else if (selectedOption === customTimeOptionName) {
      selectedTimerange.value = {
        type: 'age',
        title: _t('The last...'),
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
        title: _t('Date range'),
        date_range: {
          from: getApiDate(customDurationDate.value.from),
          to: getApiDate(customDurationDate.value.to)
        },
        duration: null,
        predefined: null,
        age: null
      }
    } else if (selectedOption in predefinedTimeranges) {
      const predefinedTitle = predefinedTimeranges[selectedOption]
      if (predefinedTitle) {
        selectedTimerange.value = {
          type: 'predefined',
          title: predefinedTitle,
          predefined: selectedOption,
          duration: null,
          date_range: null,
          age: null
        }
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
      v-model:selected-option="selectedDropdownOption"
      :options="{ type: 'fixed', suggestions: dropdownOptions }"
      :label="_t('Time range')"
    />
    <DurationFields v-if="isCustomTimeSelected" v-model="customDuration" />
    <DateRangeFields v-if="isCustomDateSelected" v-model="customDurationDate" />
  </div>
</template>
