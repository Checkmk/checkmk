/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { defineComponent, nextTick, ref } from 'vue'

import type { CustomGraphOptions } from '@/graphing/designer/api'
import {
  type DataFieldErrors,
  type ValidationResult,
  useCustomGraphOptions
} from '@/graphing/designer/composables/useCustomGraphOptions'

function autoOptions(): CustomGraphOptions {
  return {
    unit: { type: 'first_entry_with_unit' },
    explicit_vertical_range: { type: 'auto' },
    omit_zero_metrics: false
  }
}

function customUnitOptions(): CustomGraphOptions {
  return {
    unit: {
      type: 'custom',
      notation: { notation: 'decimal', symbol: 'MB' },
      precision: { type: 'strict', digits: 3 }
    },
    explicit_vertical_range: { type: 'fixed', lower: -5, upper: 10 },
    omit_zero_metrics: true
  }
}

function mountComposable(graphOptions: CustomGraphOptions) {
  return mountComposableWithGetter(() => graphOptions)
}

function mountComposableWithGetter(getGraphOptions: () => CustomGraphOptions) {
  let api!: ReturnType<typeof useCustomGraphOptions>
  render(
    defineComponent({
      setup() {
        api = useCustomGraphOptions(getGraphOptions)
        return () => null
      }
    })
  )
  return api
}

function expectValid(result: ValidationResult): CustomGraphOptions {
  if (!result.isValid) {
    throw new Error('expected the options to validate')
  }
  return result.graphOptions
}

function expectInvalid(result: ValidationResult): DataFieldErrors {
  if (result.isValid) {
    throw new Error('expected the options to fail the validation')
  }
  return result.errors
}

test('reset restores the original graph options', () => {
  const api = mountComposable(autoOptions())
  api.unitType.value = 'custom'
  api.reset()
  expect(expectValid(api.validate())).toEqual(autoOptions())
})

describe('unitType', () => {
  test('reflects the underlying unit type', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.unitType.value).toBe('custom')
  })

  test('switching to custom installs default notation and precision', () => {
    const api = mountComposable(autoOptions())
    api.unitType.value = 'custom'
    expect(expectValid(api.validate()).unit).toEqual({
      type: 'custom',
      notation: { notation: 'decimal', symbol: '' },
      precision: { type: 'auto', digits: 2 }
    })
  })

  test('switching back to first_entry_with_unit drops the custom notation', () => {
    const api = mountComposable(customUnitOptions())
    api.unitType.value = 'first_entry_with_unit'
    expect(expectValid(api.validate()).unit).toEqual({ type: 'first_entry_with_unit' })
  })
})

describe('notation', () => {
  test('is null when the unit is not custom', () => {
    const api = mountComposable(autoOptions())
    expect(api.notation.value).toBeNull()
    api.notation.value = 'si'
    expect(api.notation.value).toBeNull()
  })

  test('reflects the custom unit notation', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.notation.value).toBe('decimal')
  })

  test('switching to time drops the symbol', () => {
    const api = mountComposable(customUnitOptions())
    api.notation.value = 'time'
    expect(expectValid(api.validate()).unit).toMatchObject({ notation: { notation: 'time' } })
    expect(api.symbol.value).toBe('')
  })

  test('switching between symbol notations preserves the existing symbol', () => {
    const api = mountComposable(customUnitOptions())
    api.notation.value = 'si'
    expect(api.notation.value).toBe('si')
    expect(api.symbol.value).toBe('MB')
  })

  test('switching away from time resets the symbol to empty', () => {
    const api = mountComposable(customUnitOptions())
    api.notation.value = 'time'
    api.notation.value = 'decimal'
    expect(api.symbol.value).toBe('')
  })
})

describe('symbol', () => {
  test('is empty when the unit is not custom', () => {
    const api = mountComposable(autoOptions())
    expect(api.symbol.value).toBe('')
  })

  test('is empty for a time notation', () => {
    const api = mountComposable({
      ...customUnitOptions(),
      unit: {
        type: 'custom',
        notation: { notation: 'time' },
        precision: { type: 'auto', digits: 2 }
      }
    })
    expect(api.symbol.value).toBe('')
  })

  test('reflects and updates the custom unit symbol', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.symbol.value).toBe('MB')
    api.symbol.value = 'GB'
    expect(api.symbol.value).toBe('GB')
  })

  test('is a no-op when the unit is not custom', () => {
    const api = mountComposable(autoOptions())
    api.symbol.value = 'GB'
    expect(api.symbol.value).toBe('')
  })
})

describe('roundingMode', () => {
  test('is null when the unit is not custom', () => {
    const api = mountComposable(autoOptions())
    expect(api.roundingMode.value).toBeNull()
  })

  test('reflects and updates the custom unit precision type', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.roundingMode.value).toBe('strict')
    api.roundingMode.value = 'auto'
    expect(api.roundingMode.value).toBe('auto')
  })

  test('is a no-op when the unit is not custom', () => {
    const api = mountComposable(autoOptions())
    api.roundingMode.value = 'strict'
    expect(api.roundingMode.value).toBeNull()
  })
})

describe('roundingDigits', () => {
  test('is undefined when the unit is not custom', () => {
    const api = mountComposable(autoOptions())
    expect(api.roundingDigits.value).toBeUndefined()
  })

  test('reflects and updates the custom unit precision digits', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.roundingDigits.value).toBe(3)
    api.roundingDigits.value = 5
    expect(api.roundingDigits.value).toBe(5)
  })

  test('setting undefined resets digits to the default of 2', () => {
    const api = mountComposable(customUnitOptions())
    api.roundingDigits.value = undefined
    expect(api.roundingDigits.value).toBe(2)
  })

  test('is a no-op when the unit is not custom', () => {
    const api = mountComposable(autoOptions())
    api.roundingDigits.value = 5
    expect(api.roundingDigits.value).toBeUndefined()
  })
})

describe('verticalRangeType', () => {
  test('reflects the underlying vertical range type', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.verticalRangeType.value).toBe('fixed')
  })

  test('switching to fixed installs default lower/upper bounds', () => {
    const api = mountComposable(autoOptions())
    api.verticalRangeType.value = 'fixed'
    expect(expectValid(api.validate()).explicit_vertical_range).toEqual({
      type: 'fixed',
      lower: 0,
      upper: 1
    })
  })

  test('switching back to auto drops the bounds', () => {
    const api = mountComposable(customUnitOptions())
    api.verticalRangeType.value = 'auto'
    expect(expectValid(api.validate()).explicit_vertical_range).toEqual({ type: 'auto' })
  })
})

describe('lowerVerticalRange / upperVerticalRange', () => {
  test('are null when the range is auto', () => {
    const api = mountComposable(autoOptions())
    expect(api.lowerVerticalRange.value).toBeNull()
    expect(api.upperVerticalRange.value).toBeNull()
  })

  test('reflect the fixed range bounds', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.lowerVerticalRange.value).toBe(-5)
    expect(api.upperVerticalRange.value).toBe(10)
  })

  test('update the fixed range bounds', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = -20
    api.upperVerticalRange.value = 20
    expect(api.lowerVerticalRange.value).toBe(-20)
    expect(api.upperVerticalRange.value).toBe(20)
  })

  test('clearing a fixed bound keeps it null instead of defaulting', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = null
    api.upperVerticalRange.value = null
    expect(api.lowerVerticalRange.value).toBeNull()
    expect(api.upperVerticalRange.value).toBeNull()
  })

  test('clearing only the lower bound leaves the upper bound untouched', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = null
    expect(api.lowerVerticalRange.value).toBeNull()
    expect(api.upperVerticalRange.value).toBe(10)
  })

  test('setting a value after it was null replaces the null', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = null
    api.lowerVerticalRange.value = -8
    expect(api.lowerVerticalRange.value).toBe(-8)
  })

  test('empty string and NaN are normalized to null, not passed through', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = '' as unknown as number
    expect(api.lowerVerticalRange.value).toBeNull()
    api.upperVerticalRange.value = NaN
    expect(api.upperVerticalRange.value).toBeNull()
  })

  test('are a no-op when the range is auto', () => {
    const api = mountComposable(autoOptions())
    api.lowerVerticalRange.value = -20
    api.upperVerticalRange.value = 20
    expect(api.lowerVerticalRange.value).toBeNull()
    expect(api.upperVerticalRange.value).toBeNull()
  })
})

describe('showZeroValues', () => {
  test('is the negation of omit_zero_metrics', () => {
    const api = mountComposable(customUnitOptions())
    expect(api.showZeroValues.value).toBe(false)
  })

  test('setting it updates omit_zero_metrics accordingly', () => {
    const api = mountComposable(autoOptions())
    api.showZeroValues.value = false
    expect(expectValid(api.validate()).omit_zero_metrics).toBe(true)
    api.showZeroValues.value = true
    expect(expectValid(api.validate()).omit_zero_metrics).toBe(false)
  })
})

describe('validate', () => {
  test('hands back well-formed auto options unchanged', () => {
    const api = mountComposable(autoOptions())
    expect(expectValid(api.validate())).toEqual(autoOptions())
  })

  test('hands back well-formed custom/fixed options unchanged', () => {
    const api = mountComposable(customUnitOptions())
    expect(expectValid(api.validate())).toEqual(customUnitOptions())
  })

  test('flags missing rounding digits when the unit is custom', () => {
    // The roundingDigits setter always coerces to a default of 2, so an undefined value
    // can only occur in data loaded from the backend, before any setter runs.
    const options = {
      unit: {
        type: 'custom',
        notation: { notation: 'decimal', symbol: '' },
        precision: { type: 'auto', digits: undefined }
      },
      explicit_vertical_range: { type: 'auto' },
      omit_zero_metrics: false
    } as unknown as CustomGraphOptions
    const api = mountComposable(options)
    expect(api.roundingDigits.value).toBeUndefined()
    expect(expectInvalid(api.validate()).precision_digits).toBeDefined()
  })

  test('flags negative rounding digits when the unit is custom', () => {
    const api = mountComposable(customUnitOptions())
    api.roundingDigits.value = -1
    expect(expectInvalid(api.validate()).precision_digits).toBeDefined()
  })

  test.each([
    { cleared: 'lower', flagged: 'lower_range', kept: 'upper_range' },
    { cleared: 'upper', flagged: 'upper_range', kept: 'lower_range' }
  ] as const)(
    'flags a fixed range whose $cleared limit is cleared',
    ({ cleared, flagged, kept }) => {
      // A stored range names both of its edges and the preview draws none with an open end, so the
      // form refuses it here rather than letting the fetch and the save fail.
      const api = mountComposable(customUnitOptions())
      if (cleared === 'lower') {
        api.lowerVerticalRange.value = null
      } else {
        api.upperVerticalRange.value = null
      }
      const errors = expectInvalid(api.validate())
      expect(errors[flagged]).toBeDefined()
      expect(errors[kept]).toBeUndefined()
    }
  )

  test('flags a fixed range with neither limit set', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = null
    api.upperVerticalRange.value = null
    const errors = expectInvalid(api.validate())
    expect(errors.lower_range).toBeDefined()
    expect(errors.upper_range).toBeDefined()
  })

  test('hands back the edited options once they are valid', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = -20
    api.upperVerticalRange.value = 20

    // The payload is what the API takes: the draft's nullable edges are numbers by now.
    expect(expectValid(api.validate()).explicit_vertical_range).toEqual({
      type: 'fixed',
      lower: -20,
      upper: 20
    })
  })

  test('flags a fixed range with lower equal to upper', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = 5
    api.upperVerticalRange.value = 5
    const errors = expectInvalid(api.validate())
    expect(errors.lower_range).toBeDefined()
    expect(errors.upper_range).toBeDefined()
  })

  test('flags a fixed range with lower greater than upper', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = 15
    api.upperVerticalRange.value = 5
    expect(api.validate().isValid).toBe(false)
  })

  test('becomes valid again once the fixed range is corrected', () => {
    const api = mountComposable(customUnitOptions())
    api.lowerVerticalRange.value = 15
    api.upperVerticalRange.value = 5
    expect(api.validate().isValid).toBe(false)
    api.upperVerticalRange.value = 25
    expect(api.validate().isValid).toBe(true)
  })
})

describe('reactivity to the underlying source', () => {
  test('picks up a replaced graph options object', async () => {
    const source = ref<CustomGraphOptions>(autoOptions())
    const api = mountComposableWithGetter(() => source.value)

    source.value = customUnitOptions()
    await nextTick()

    expect(expectValid(api.validate())).toEqual(customUnitOptions())
  })

  test('picks up in-place mutations of the graph options object', async () => {
    const source = ref<CustomGraphOptions>(autoOptions())
    const api = mountComposableWithGetter(() => source.value)

    source.value.omit_zero_metrics = true
    await nextTick()

    expect(api.showZeroValues.value).toBe(false)
  })

  test('picks up a bound being replaced from the source', async () => {
    const source = ref<CustomGraphOptions>(customUnitOptions())
    const api = mountComposableWithGetter(() => source.value)
    expect(api.lowerVerticalRange.value).toBe(-5)

    source.value = {
      ...customUnitOptions(),
      explicit_vertical_range: { type: 'fixed', lower: -20, upper: 10 }
    }
    await nextTick()

    expect(api.lowerVerticalRange.value).toBe(-20)
    expect(api.upperVerticalRange.value).toBe(10)
  })
})
