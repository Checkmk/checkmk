/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, watch } from 'vue'

import type { RequestedTimeRange } from '../types'

export function useGraphTimeRange(getRequestedTimeRange: () => RequestedTimeRange) {
  const activeTimeRange = ref<RequestedTimeRange>({ ...getRequestedTimeRange() })

  watch(
    getRequestedTimeRange,
    (val) => {
      activeTimeRange.value = { ...val }
    },
    { deep: true }
  )

  function setActiveTimeRange(val: RequestedTimeRange) {
    activeTimeRange.value = { ...val }
  }

  return { activeTimeRange, setActiveTimeRange }
}
