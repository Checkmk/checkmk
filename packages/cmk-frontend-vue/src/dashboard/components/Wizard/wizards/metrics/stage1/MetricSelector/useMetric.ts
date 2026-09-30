/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { type Ref, ref, watch } from 'vue'

import type { LabelValueItem, UseValidate } from '@/dashboard/components/Wizard/types'

export interface UseMetric extends UseValidate {
  metric: Ref<LabelValueItem | null>
  metricValidationError: Ref<boolean>
}

export const useMetric = (
  context?: ConfiguredFilters,
  selectedMetric?: string | null
): UseMetric => {
  const metric = ref<LabelValueItem | null>(
    selectedMetric ? { value: selectedMetric, label: selectedMetric } : null
  )
  const metricValidationError = ref<boolean>(false)

  if (context) {
    watch(
      context,
      () => {
        metric.value = null
      },
      { deep: true }
    )
  }

  watch(
    [metric],
    (newMetric) => {
      metricValidationError.value = !newMetric
    },
    { deep: true }
  )

  const validate = (): boolean => {
    metricValidationError.value = !metric.value
    return !!metric.value
  }

  return {
    metric,

    metricValidationError,
    validate
  }
}
