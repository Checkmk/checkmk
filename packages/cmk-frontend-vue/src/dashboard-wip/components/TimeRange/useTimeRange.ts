/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { GraphTimerange } from './GraphTimeRange.vue'
import type { TimerangeModel } from './types'

interface UseTimeRange {
  timeRange: Ref<GraphTimerange>
  widgetProps: () => TimerangeModel
}

export const useTimeRange = (title: TranslatedString): UseTimeRange => {
  //Todo: Fill values if they exist in serializedData
  const timeRange = ref<GraphTimerange>({
    type: 'predefined',
    title: title,
    duration: null,
    date_range: null,
    predefined: 'last_4_hours',
    age: null
  })

  const widgetProps = (): TimerangeModel => {
    let window: TimerangeModel
    switch (timeRange.value.type) {
      case 'duration':
        window = {
          type: 'graph',
          duration: timeRange.value.duration!
        }
        break

      case 'date':
        window = {
          type: 'date',
          start: timeRange.value.date_range!.from,
          end: timeRange.value.date_range!.to
        }
        break

      case 'age':
        window = {
          type: 'age'
        }

        if (timeRange.value.age?.days) {
          window.days = timeRange.value.age.days
        }

        if (timeRange.value.age?.hours) {
          window.hours = timeRange.value.age.hours
        }

        if (timeRange.value.age?.minutes) {
          window.minutes = timeRange.value.age.minutes
        }

        if (timeRange.value.age?.seconds) {
          window.seconds = timeRange.value.age.seconds
        }
        break

      //case 'predefined':
      default:
        window = {
          type: 'predefined',
          value: timeRange.value.predefined!
        }
        break
    }

    return window
  }

  return {
    timeRange,
    widgetProps
  }
}
