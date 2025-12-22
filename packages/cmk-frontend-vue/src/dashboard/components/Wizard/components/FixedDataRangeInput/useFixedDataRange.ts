/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

import type { FixedDataRangeModel } from '../../types'

interface UseFixedDataRange {
  symbol: Ref<string>
  minimum: Ref<number>
  maximum: Ref<number>

  fixedDataRangeProps: Ref<FixedDataRangeModel>

  /**
   * use fixedDataRangeProps ref instead
   * @deprecated
   * @returns FixedDataRangeModel
   */
  widgetProps: () => FixedDataRangeModel
}

export const useFixedDataRange = (
  symbol: string | null = null,
  minimum: number | null = null,
  maximum: number | null = null
): UseFixedDataRange => {
  const dataSymbol = ref<string>(symbol || 'DecimalNotation__AutoPrecision_2')
  const dataMin = ref<number>(minimum || 0)
  const dataMax = ref<number>(maximum || 100)

  const fixedDataRangeProps = computed((): FixedDataRangeModel => {
    return {
      type: 'fixed',
      unit: dataSymbol.value,
      minimum: dataMin.value,
      maximum: dataMax.value
    }
  })

  const widgetProps = (): FixedDataRangeModel => {
    return fixedDataRangeProps.value
  }

  return {
    symbol: dataSymbol,
    minimum: dataMin,
    maximum: dataMax,
    fixedDataRangeProps,

    widgetProps
  }
}
