/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { type Ref, computed, ref } from 'vue'

import type { CustomGraphOptions, CustomGraphUnitNotationTypes } from '../api'

const { _t } = usei18n()

type DataFields = 'precision_digits' | 'lower_range' | 'upper_range'
export type DataFieldErrors = Partial<Record<DataFields, TranslatedString>>

type DraftVerticalRange =
  | { type: 'auto' }
  | { type: 'fixed'; lower: number | null; upper: number | null }

interface DraftGraphOptions {
  unit: CustomGraphOptions['unit']
  explicit_vertical_range: DraftVerticalRange
  omit_zero_metrics: boolean
}

export type ValidationResult =
  | { isValid: true; graphOptions: CustomGraphOptions }
  | { isValid: false; errors: DataFieldErrors }

interface UseCustomGraphOptions {
  unitType: Ref<'first_entry_with_unit' | 'custom'>
  notation: Ref<CustomGraphUnitNotationTypes | 'time' | null>
  symbol: Ref<string>
  roundingMode: Ref<'auto' | 'strict' | null>
  roundingDigits: Ref<number | undefined>

  verticalRangeType: Ref<string>
  lowerVerticalRange: Ref<number | null>
  upperVerticalRange: Ref<number | null>

  showZeroValues: Ref<boolean>

  validate: () => ValidationResult
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
  const graphOptions = ref<DraftGraphOptions>(JSON.parse(JSON.stringify(getGraphOptions())))

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
    get: () => graphOptions.value.unit.type,
    set: (value: 'first_entry_with_unit' | 'custom') => {
      graphOptions.value.unit =
        value === 'custom'
          ? {
              type: 'custom',
              notation: { notation: 'decimal', symbol: '' },
              precision: { type: 'auto', digits: 2 }
            }
          : { type: 'first_entry_with_unit' }
    }
  })

  const notation = computed({
    get: () =>
      graphOptions.value.unit.type === 'custom' ? graphOptions.value.unit.notation.notation : null,
    set: (newNotation) => {
      if (graphOptions.value.unit.type !== 'custom' || !newNotation) {
        return
      }

      if (newNotation === 'time') {
        graphOptions.value.unit.notation = { notation: newNotation }
      } else {
        graphOptions.value.unit.notation = {
          notation: newNotation,
          symbol:
            graphOptions.value.unit.notation.notation !== 'time'
              ? graphOptions.value.unit.notation.symbol
              : ''
        }
      }
    }
  })

  const symbol = computed({
    get: () => {
      const unit = graphOptions.value.unit
      return unit.type === 'custom' && unit.notation.notation !== 'time' ? unit.notation.symbol : ''
    },
    set: (newSymbol: string) => {
      const unit = graphOptions.value.unit
      if (unit.type === 'custom' && unit.notation.notation !== 'time') {
        unit.notation.symbol = newSymbol
      }
    }
  })

  const roundingMode = computed({
    get: () => {
      const unit = graphOptions.value.unit
      return unit.type === 'custom' ? unit.precision.type : null
    },
    set: (newRoundingMode: 'auto' | 'strict') => {
      const unit = graphOptions.value.unit
      if (unit.type === 'custom') {
        unit.precision.type = newRoundingMode
      }
    }
  })

  const roundingDigits = computed({
    get: (): number | undefined => {
      const unit = graphOptions.value.unit
      return unit.type === 'custom' ? unit.precision.digits : undefined
    },
    set: (value: number | undefined) => {
      const unit = graphOptions.value.unit
      if (unit.type === 'custom') {
        unit.precision.digits = value ?? 2
      }
    }
  })

  // Vertical range settings
  const verticalRangeType = computed({
    get: () => graphOptions.value.explicit_vertical_range.type,
    set: (value: string) => {
      graphOptions.value.explicit_vertical_range =
        value === 'fixed' ? { type: 'fixed', lower: 0, upper: 1 } : { type: 'auto' }
    }
  })

  const lowerVerticalRange = computed({
    get: (): number | null => {
      const range = graphOptions.value.explicit_vertical_range
      return range.type === 'fixed' ? range.lower : null
    },
    set: (value: number | null) => {
      const range = graphOptions.value.explicit_vertical_range
      if (range.type === 'fixed') {
        range.lower = _isValidNumber(value) ? value : null
      }
    }
  })

  const upperVerticalRange = computed({
    get: (): number | null => {
      const range = graphOptions.value.explicit_vertical_range
      return range.type === 'fixed' ? range.upper : null
    },
    set: (value: number | null) => {
      const range = graphOptions.value.explicit_vertical_range
      if (range.type === 'fixed') {
        range.upper = _isValidNumber(value) ? value : null
      }
    }
  })

  // Show zero values setting
  const showZeroValues = computed({
    get: () => !graphOptions.value.omit_zero_metrics,
    set: (value: boolean) => {
      graphOptions.value.omit_zero_metrics = !value
    }
  })

  const validate = (): ValidationResult => {
    const errors: DataFieldErrors = {}
    const draft = graphOptions.value

    if (
      draft.unit.type === 'custom' &&
      (!_isValidInteger(draft.unit.precision.digits) || draft.unit.precision.digits < 0)
    ) {
      errors.precision_digits = _t(
        'The number of digits for rounding must be a non-negative integer'
      )
    }

    const range = draft.explicit_vertical_range
    let checkedRange: CustomGraphOptions['explicit_vertical_range'] | null = null
    if (range.type === 'auto') {
      checkedRange = range
    } else if (range.lower === null || range.upper === null) {
      const message = _t('Set both limits, or scale the range automatically')
      if (range.lower === null) {
        errors.lower_range = message
      }
      if (range.upper === null) {
        errors.upper_range = message
      }
    } else if (range.lower >= range.upper) {
      errors.lower_range = _t('The lower limit must be less than the upper limit')
      errors.upper_range = _t('The upper limit must be greater than the lower limit')
    } else {
      checkedRange = { type: 'fixed', lower: range.lower, upper: range.upper }
    }

    if (checkedRange === null || Object.keys(errors).length > 0) {
      return { isValid: false, errors }
    }
    return { isValid: true, graphOptions: { ...draft, explicit_vertical_range: checkedRange } }
  }

  return {
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
