/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import type { UseValidate } from '@/dashboard-wip/components/Wizard/types'

export interface UseMetric extends UseValidate {
  host: Ref<string | null>
  service: Ref<string | null>
  metric: Ref<string | null>

  metricValidationError: Ref<boolean>
}

export const useMetric = (
  hostName?: string | null,
  serviceDescription?: string | null,
  selectedMetric?: string | null
): UseMetric => {
  const host = ref<string | null>(hostName || null)
  const service = ref<string | null>(serviceDescription || null)
  const metric = ref<string | null>(selectedMetric || null)
  const metricValidationError = ref<boolean>(false)

  watch([host.value], () => {
    service.value = null
    metric.value = null
  })

  watch([service.value], () => {
    metric.value = null
  })

  const validate = (): boolean => {
    metricValidationError.value = !metric.value
    return !!metric.value
  }

  return {
    host,
    service,
    metric,

    metricValidationError,
    validate
  }
}
