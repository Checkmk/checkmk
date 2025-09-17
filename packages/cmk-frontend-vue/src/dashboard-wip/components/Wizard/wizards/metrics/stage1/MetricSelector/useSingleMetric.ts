/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { MetricHandler } from './types'

export interface UseSingleMetric extends MetricHandler {
  host: Ref<string | null>
  service: Ref<string | null>
  singleMetric: Ref<string | null>

  singleMetricValidationError: Ref<boolean>
}

export const useSingleMetric = (
  hostName?: string | null,
  serviceDescription?: string | null,
  singleMetric?: string | null
): UseSingleMetric => {
  const host = ref<string | null>(hostName || null)
  const service = ref<string | null>(serviceDescription || null)
  const metric = ref<string | null>(singleMetric || null)
  const singleMetricValidationError = ref<boolean>(false)

  watch(
    () => host.value,
    () => {
      service.value = null
      metric.value = null
    }
  )

  watch(
    () => service.value,
    () => {
      metric.value = null
    }
  )

  const validate = (): boolean => {
    singleMetricValidationError.value = !metric.value
    return !!metric.value
  }

  return {
    host: host,
    service: service,
    singleMetric: metric,

    singleMetricValidationError,
    validate
  }
}
