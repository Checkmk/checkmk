/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { GraphTimerange } from './GraphTimeRange.vue'
import type { TimerangeModel } from './types'

interface UseTimeRange {
  timeRange: Ref<GraphTimerange>
  widgetProps: () => TimerangeModel
}

const timerangeModel2GraphTimerange = (model: TimerangeModel): GraphTimerange => {
  switch (model?.type) {
    case 'graph':
      return {
        type: 'duration',
        duration: model.duration,
        title: null,
        date_range: null,
        predefined: null,
        age: null
      }

    case 'date':
      return {
        type: 'date',
        date_range: {
          from: model.start,
          to: model.end
        },
        title: null,
        duration: null,
        predefined: null,
        age: null
      }

    case 'age':
      return {
        type: 'age',
        age: {
          days: model.days ?? 0,
          hours: model.hours ?? 0,
          minutes: model.minutes ?? 0,
          seconds: model.seconds ?? 0
        },
        title: null,
        duration: null,
        date_range: null,
        predefined: null
      }

    case 'predefined':
    default:
      return {
        type: 'predefined',
        predefined: model.value,
        title: null,
        duration: null,
        date_range: null,
        age: null
      }
  }
}

export const useTimeRange = (currentTimerange: TimerangeModel | null): UseTimeRange => {
  const timeRange = ref<GraphTimerange>({
    type: 'predefined',
    predefined: 'last_4_hours',
    title: null,
    duration: null,
    date_range: null,
    age: null
  })
  if (currentTimerange) {
    timeRange.value = timerangeModel2GraphTimerange(currentTimerange)
  }

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
