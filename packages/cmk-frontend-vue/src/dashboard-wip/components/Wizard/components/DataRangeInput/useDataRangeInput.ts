/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { MetricDisplayRangeModel } from '../../types'
import { useFixedDataRange } from '../FixedDataRangeInput/useFixedDataRange'

export type DataRangeType = 'fixed' | 'automatic'
export interface UseDataRangeInput {
  type: Ref<DataRangeType>
  symbol: Ref<string>
  minimum: Ref<number>
  maximum: Ref<number>

  widgetProps: () => MetricDisplayRangeModel
}

export const useDataRangeInput = (): UseDataRangeInput => {
  const dataRangeType = ref<DataRangeType>('automatic')
  const { symbol, maximum, minimum, widgetProps: fixedDataRangeProps } = useFixedDataRange()

  const widgetProps = (): MetricDisplayRangeModel => {
    return dataRangeType.value === 'automatic' ? 'automatic' : fixedDataRangeProps()
  }

  return {
    type: dataRangeType,
    symbol,
    maximum,
    minimum,

    widgetProps
  }
}
