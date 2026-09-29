/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { GraphTimerange } from './GraphTimeRange.vue'
import type { TimerangeModel } from './types'
import { useTimeRange } from './useTimeRange'

export type TimeRangeSourceModel = 'dashboard' | TimerangeModel

interface UseTimeRangeSource {
  followDashboard: Ref<boolean>
  timeRange: Ref<GraphTimerange>
  widgetProps: () => TimeRangeSourceModel
}

/** A widget time range that either follows the dashboard or holds its own range. */
export const useTimeRangeSource = (current: TimeRangeSourceModel | null): UseTimeRangeSource => {
  const followDashboard = ref(current === null || current === 'dashboard')
  const { timeRange, widgetProps: separateTimeRange } = useTimeRange(
    current === null || current === 'dashboard' ? null : current
  )

  return {
    followDashboard,
    timeRange,
    widgetProps: () => (followDashboard.value ? 'dashboard' : separateTimeRange())
  }
}
