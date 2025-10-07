/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { MetricHandler } from './types'

export interface UseCombinedMetric extends MetricHandler {
  combinedMetric: Ref<string | null>

  combinedMetricValidationError: Ref<boolean>
}

export const useCombinedMetric = (combinedMetric?: string | null): UseCombinedMetric => {
  const metric = ref<string | null>(combinedMetric || null)
  const combinedMetricValidationError = ref<boolean>(false)

  const validate = (): boolean => {
    combinedMetricValidationError.value = !metric.value
    return !!metric.value
  }

  return {
    combinedMetric: metric,

    combinedMetricValidationError,

    validate
  }
}
