/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useDataRangeInput } from '@/dashboard/components/Wizard/components/DataRangeInput/useDataRangeInput'
import type { FixedDataRangeModel } from '@/dashboard/components/Wizard/types'

describe('useDataRangeInput', () => {
  describe('initialization', () => {
    it('should default to fixed type when called with no arguments', () => {
      const { type } = useDataRangeInput()
      expect(type.value).toBe('fixed')
    })

    it('should set type to automatic and return "automatic" from dataRangeProps when initialized with "automatic"', () => {
      const { type, dataRangeProps } = useDataRangeInput('automatic')
      expect(type.value).toBe('automatic')
      expect(dataRangeProps.value).toBe('automatic')
    })

    it('should set type to fixed and pass values to inner composable when initialized with FixedDataRangeModel', () => {
      const fixedData: FixedDataRangeModel = {
        type: 'fixed',
        unit: 'Percent',
        minimum: 10,
        maximum: 90
      }
      const { type, symbol, minimum, maximum } = useDataRangeInput(fixedData)
      expect(type.value).toBe('fixed')
      expect(symbol.value).toBe('Percent')
      expect(minimum.value).toBe(10)
      expect(maximum.value).toBe(90)
    })
  })

  describe('dataRangeProps computed', () => {
    it('should return FixedDataRangeModel when type is fixed', () => {
      const { dataRangeProps } = useDataRangeInput()
      expect(dataRangeProps.value).toEqual({
        type: 'fixed',
        unit: 'DecimalNotation__AutoPrecision_2',
        minimum: 0,
        maximum: 100
      })
    })

    it('should update reactively when type changes', () => {
      const { type, dataRangeProps } = useDataRangeInput()
      expect(dataRangeProps.value).toEqual(expect.objectContaining({ type: 'fixed' }))

      type.value = 'automatic'
      expect(dataRangeProps.value).toBe('automatic')

      type.value = 'fixed'
      expect(dataRangeProps.value).toEqual(expect.objectContaining({ type: 'fixed' }))
    })
  })
})
