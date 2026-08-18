/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref } from 'vue'

import type { RequestedTimeRange } from '../types'
import type { RequestedTimeRangeState } from './useRequestedTimeRange'

/**
 * The requested time range of a graph owner that answers to nobody but itself.
 *
 * Same shape as `useRequestedTimeRange`, without the page's global time picker: the range
 * starts at `initial` and only the owner's own zooms, pans and brushes move it. For an embed
 * that lives beside a page it must not steer - a slide-in panel, say - where following the
 * picker would let a zoom in the embed move the graphs behind it.
 */
export function useLocalTimeRange(initial: RequestedTimeRange): RequestedTimeRangeState {
  const request = ref<RequestedTimeRange>({ ...initial })

  return {
    requestedTimeRange: computed(() => request.value),
    setRequestedTimeRange: (range: RequestedTimeRange) => {
      request.value = { start: range.start, end: range.end }
    },
    timePickerRequests: computed(() => 0)
  }
}
