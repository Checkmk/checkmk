/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

import type { FixedDataRangeModel, MetricDisplayRangeModel } from '../../types'
import { useFixedDataRange } from '../FixedDataRangeInput/useFixedDataRange'

export type DataRangeType = 'fixed' | 'automatic'
export interface UseDataRangeInput {
  type: Ref<DataRangeType>
  symbol: Ref<string>
  minimum: Ref<number>
  maximum: Ref<number>

  dataRangeProps: Ref<MetricDisplayRangeModel>

  /**
   * use dataRangeProps ref instead
   * @deprecated
   * @returns MetricDisplayRangeModel
   */
  widgetProps: () => MetricDisplayRangeModel
}

export const useDataRangeInput = (data?: MetricDisplayRangeModel): UseDataRangeInput => {
  const dataRangeType = ref<DataRangeType>(data === 'automatic' ? 'automatic' : 'fixed')

  const fixedDataRange = data as FixedDataRangeModel
  const { symbol, maximum, minimum, fixedDataRangeProps } = useFixedDataRange(
    fixedDataRange?.unit,
    fixedDataRange?.minimum,
    fixedDataRange?.maximum
  )

  const dataRangeProps = computed((): MetricDisplayRangeModel => {
    return dataRangeType.value === 'automatic' ? 'automatic' : fixedDataRangeProps.value
  })

  const widgetProps = (): MetricDisplayRangeModel => {
    return dataRangeProps.value
  }

  return {
    type: dataRangeType,
    symbol,
    maximum,
    minimum,
    dataRangeProps,

    widgetProps
  }
}
