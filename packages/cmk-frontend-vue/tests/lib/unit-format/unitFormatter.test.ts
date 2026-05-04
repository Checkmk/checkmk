/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  DecimalFormatter,
  IECFormatter,
  SIFormatter,
  TimeFormatter
} from '@/lib/unit-format/notationFormatter'
import { type UnitFormat, userSpecificUnit } from '@/lib/unit-format/unitFormatter'

const auto2 = { type: 'auto', digits: 2 } as const

describe('userSpecificUnit dispatcher', () => {
  test.each<[UnitFormat['notation'], new (...args: never[]) => unknown]>([
    ['decimal', DecimalFormatter],
    ['si', SIFormatter],
    ['iec', IECFormatter],
    ['time', TimeFormatter]
  ])('returns the right formatter class for notation=%s', (notation, expectedClass) => {
    const { formatter } = userSpecificUnit(
      { notation, symbol: 'unit', precision: auto2 },
      'celsius'
    )
    expect(formatter.constructor).toBe(expectedClass)
  })

  test('passes precision through to the formatter', () => {
    const { formatter } = userSpecificUnit(
      { notation: 'decimal', symbol: 'unit', precision: { type: 'strict', digits: 0 } },
      'celsius'
    )
    expect(formatter.render(0.6789)).toBe('1 unit')
  })
})

describe('temperature conversion', () => {
  test('°C value with celsius preference renders as °C, identity convert', () => {
    const { formatter, convert } = userSpecificUnit(
      { notation: 'decimal', symbol: '°C', precision: auto2 },
      'celsius'
    )
    expect(convert(0)).toBe(0)
    expect(convert(100)).toBe(100)
    expect(formatter.render(20)).toBe('20 °C')
  })

  test('°C value with fahrenheit preference converts and renders as °F', () => {
    const { formatter, convert } = userSpecificUnit(
      { notation: 'decimal', symbol: '°C', precision: auto2 },
      'fahrenheit'
    )
    expect(convert(0)).toBe(32)
    expect(convert(100)).toBe(212)
    expect(formatter.render(convert(20))).toBe('68 °F')
  })

  test('°F value with celsius preference converts and renders as °C', () => {
    const { formatter, convert } = userSpecificUnit(
      { notation: 'decimal', symbol: '°F', precision: auto2 },
      'celsius'
    )
    expect(convert(32)).toBe(0)
    expect(convert(212)).toBe(100)
    expect(formatter.render(convert(212))).toBe('100 °C')
  })

  test('°F value with fahrenheit preference is identity', () => {
    const { formatter, convert } = userSpecificUnit(
      { notation: 'decimal', symbol: '°F', precision: auto2 },
      'fahrenheit'
    )
    expect(convert(98.6)).toBe(98.6)
    expect(formatter.render(98.6)).toBe('98.6 °F')
  })

  test('non-temperature symbol is unaffected by user preference', () => {
    const { formatter, convert } = userSpecificUnit(
      { notation: 'si', symbol: 'B', precision: auto2 },
      'fahrenheit'
    )
    expect(convert(1234)).toBe(1234)
    expect(formatter.render(1234)).toBe('1.23 kB')
  })

  test('convertible=false suppresses temperature conversion even for °C', () => {
    const { formatter, convert } = userSpecificUnit(
      { notation: 'decimal', symbol: '°C', precision: auto2, convertible: false },
      'fahrenheit'
    )
    expect(convert(20)).toBe(20)
    expect(formatter.render(20)).toBe('20 °C')
  })

  test('symbol matching a prototype property does not resolve the inherited member', () => {
    // Regression: `spec.symbol in TEMPERATURE_CONVERSION` previously walked the
    // prototype chain and returned `Object.prototype.toString` — calling it
    // crashed downstream. With `Object.hasOwn` we get the identity converter.
    const { formatter, convert } = userSpecificUnit(
      { notation: 'decimal', symbol: 'toString', precision: auto2 },
      'celsius'
    )
    expect(convert(42)).toBe(42)
    expect(formatter.render(42)).toBe('42 toString')
  })
})
