/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { type Ref, computed, readonly, ref } from 'vue'

import type { CustomGraphOptions, CustomGraphUnitNotationTypes } from '../api'

const { _t } = usei18n()

type DataFields = 'precision_digits' | 'lower_range' | 'upper_range'
export type DataFieldErrors = Partial<Record<DataFields, TranslatedString>>
interface ValidationError {
  isValid: boolean
  errors: DataFieldErrors
}

interface UseCustomGraphOptions {
  graphOptions: Ref<CustomGraphOptions | null>

  unitType: Ref<'first_entry_with_unit' | 'custom'>
  notation: Ref<CustomGraphUnitNotationTypes | 'time' | null>
  symbol: Ref<string>
  roundingMode: Ref<'auto' | 'strict' | null>
  roundingDigits: Ref<number | undefined>

  verticalRangeType: Ref<string>
  lowerVerticalRange: Ref<number | null>
  upperVerticalRange: Ref<number | null>

  showZeroValues: Ref<boolean>

  validate: () => ValidationError
  reset: () => void
}

const _isValidNumber = (value: number | string | null | undefined): boolean => {
  return value !== undefined && value !== null && value !== '' && !isNaN(Number(value))
}

const _isValidInteger = (value: number | string | null | undefined): boolean => {
  return _isValidNumber(value) && Number.isInteger(Number(value))
}

export const useCustomGraphOptions = (
  getGraphOptions: () => CustomGraphOptions
): UseCustomGraphOptions => {
  const graphOptions = ref<CustomGraphOptions>(JSON.parse(JSON.stringify(getGraphOptions())))

  immediateWatch(
    getGraphOptions,
    (newGraphOptions) => {
      graphOptions.value = JSON.parse(JSON.stringify(newGraphOptions))
    },
    { deep: true }
  )

  const reset = () => {
    graphOptions.value = JSON.parse(JSON.stringify(getGraphOptions()))
  }

  // Unit settings
  const unitType = computed({
    get: (): 'first_entry_with_unit' | 'custom' =>
      graphOptions.value?.unit?.type ?? 'first_entry_with_unit',
    set: (value) => {
      if (!graphOptions.value?.unit) {
        return
      }

      if (value === 'first_entry_with_unit') {
        graphOptions.value.unit = { type: 'first_entry_with_unit' }
      } else if (value === 'custom') {
        graphOptions.value.unit = {
          type: 'custom',
          notation: { notation: 'decimal', symbol: '' },
          precision: { type: 'auto', digits: 2 }
        }
      }
    }
  })

  const notation = computed({
    get: () =>
      graphOptions.value?.unit?.type === 'custom'
        ? graphOptions.value.unit.notation.notation
        : null,
    set: (newNotation) => {
      if (graphOptions.value?.unit?.type !== 'custom' || !newNotation) {
        return
      }

      if (newNotation === 'time') {
        graphOptions.value.unit.notation = { notation: newNotation }
      } else {
        graphOptions.value.unit.notation = {
          notation: newNotation,
          symbol:
            graphOptions.value.unit?.notation.notation !== 'time'
              ? (graphOptions.value.unit.notation?.symbol ?? '')
              : ''
        }
      }
    }
  })

  const symbol = computed({
    get: () => {
      const unitOptions = graphOptions.value?.unit
      if (unitOptions?.type === 'custom' && unitOptions.notation.notation !== 'time') {
        return unitOptions.notation.symbol
      }
      return ''
    },
    set: (newSymbol: string) => {
      if (
        graphOptions.value?.unit?.type === 'custom' &&
        graphOptions.value?.unit.notation.notation !== 'time'
      ) {
        graphOptions.value.unit.notation.symbol = newSymbol
      }
    }
  })

  const roundingMode = computed({
    get: () => {
      const unitOptions = graphOptions.value?.unit
      return unitOptions?.type === 'custom' ? unitOptions.precision.type : null
    },
    set: (newRoundingMode: 'auto' | 'strict') => {
      if (graphOptions.value?.unit?.type === 'custom') {
        graphOptions.value.unit.precision.type = newRoundingMode
      }
    }
  })

  const roundingDigits = computed({
    get: (): number | undefined => {
      const unitOptions = graphOptions.value?.unit
      return unitOptions?.type === 'custom' ? unitOptions.precision.digits : undefined
    },
    set: (value: number | undefined) => {
      if (graphOptions.value?.unit?.type === 'custom') {
        graphOptions.value.unit.precision.digits = value ?? 2
      }
    }
  })

  // Vertical range settings
  const verticalRangeType = computed({
    get: () => graphOptions.value?.explicit_vertical_range?.type ?? 'auto',
    set: (value: string) => {
      if (graphOptions.value) {
        if (value === 'fixed') {
          graphOptions.value.explicit_vertical_range = { type: 'fixed', lower: 0, upper: 1 }
        } else {
          graphOptions.value.explicit_vertical_range = { type: 'auto' }
        }
      }
    }
  })

  const lowerVerticalRange = computed({
    get: (): number | null =>
      graphOptions.value?.explicit_vertical_range?.type === 'fixed'
        ? graphOptions.value.explicit_vertical_range.lower
        : null,
    set: (value: number | null) => {
      if (graphOptions.value?.explicit_vertical_range?.type === 'fixed') {
        graphOptions.value.explicit_vertical_range.lower = _isValidNumber(value) ? value : null
      }
    }
  })

  const upperVerticalRange = computed({
    get: (): number | null =>
      graphOptions.value?.explicit_vertical_range?.type === 'fixed'
        ? graphOptions.value.explicit_vertical_range.upper
        : null,
    set: (value: number | null) => {
      if (graphOptions.value?.explicit_vertical_range?.type === 'fixed') {
        graphOptions.value.explicit_vertical_range.upper = _isValidNumber(value) ? value : null
      }
    }
  })

  // Show zero values setting
  const showZeroValues = computed({
    get: () => !graphOptions.value?.omit_zero_metrics,
    set: (value: boolean) => graphOptions.value && (graphOptions.value.omit_zero_metrics = !value)
  })

  const validate = (): ValidationError => {
    const errors: DataFieldErrors = {}

    if (
      unitType.value === 'custom' &&
      (!_isValidInteger(roundingDigits.value) || roundingDigits.value! < 0)
    ) {
      errors.precision_digits = _t(
        'The number of digits for rounding must be a non-negative integer'
      )
    }

    if (
      verticalRangeType.value === 'fixed' &&
      _isValidNumber(lowerVerticalRange.value) &&
      _isValidNumber(upperVerticalRange.value)
    ) {
      if (lowerVerticalRange.value! >= upperVerticalRange.value!) {
        errors.lower_range = _t('The lower limit must be less than the upper limit')
        errors.upper_range = _t('The upper limit must be greater than the lower limit')
      }
    }

    return { isValid: Object.keys(errors).length === 0, errors }
  }

  return {
    graphOptions: readonly(graphOptions),

    unitType,
    notation,
    symbol,
    roundingMode,
    roundingDigits,

    verticalRangeType,
    lowerVerticalRange,
    upperVerticalRange,

    showZeroValues,

    validate,
    reset
  }
}
