/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  DecimalFormatter,
  EngineeringScientificFormatter,
  IECFormatter,
  type Label,
  type NegativeYRange,
  type NotationFormatter,
  type PositiveYRange,
  type Precision,
  SIFormatter,
  StandardScientificFormatter,
  TimeFormatter,
  stringifySmallDecimalNumber
} from '@/lib/unit-format/notationFormatter'

const pos = (start: number, end: number): PositiveYRange => ({ kind: 'positive', start, end })
const neg = (start: number, end: number): NegativeYRange => ({ kind: 'negative', start, end })

// THIN SPACE (U+2009) — DecimalFormatter's thousands separator.
const TS = ' '

const auto = (digits: number): Precision => ({ type: 'auto', digits })
const strict = (digits: number): Precision => ({ type: 'strict', digits })

describe('DecimalFormatter precision', () => {
  test.each<[Precision, number, string]>([
    [auto(0), 0, '0 unit'],
    [auto(0), 1, '1 unit'],
    [auto(0), 0.006789, '0.007 unit'],
    [strict(0), 0.006789, '0 unit'],
    [auto(1), 0.006789, '0.007 unit'],
    [strict(1), 0.006789, '0 unit'],
    [auto(0), 0.6789, '1 unit'],
    [strict(0), 0.6789, '1 unit'],
    [auto(1), 0.6789, '0.7 unit'],
    [strict(1), 0.6789, '0.7 unit'],
    // Large values exercise the THIN-SPACE thousands separator (mirrors the
    // Python `large-zeros-*` and `large-no-zeros-*` fixtures in
    // `tests/unit/cmk/gui/test_unit_formatter.py`).
    [auto(0), 12345.006789, `12${TS}345.007 unit`],
    [strict(0), 12345.006789, `12${TS}345 unit`],
    [auto(1), 12345.006789, `12${TS}345.007 unit`],
    [strict(1), 12345.006789, `12${TS}345 unit`],
    [auto(0), 12345.6789, `12${TS}346 unit`],
    [strict(0), 12345.6789, `12${TS}346 unit`],
    [auto(1), 12345.6789, `12${TS}345.7 unit`],
    [strict(1), 12345.6789, `12${TS}345.7 unit`]
  ])('precision=%j value=%s -> %s', (precision, value, expected) => {
    expect(new DecimalFormatter('unit', precision).render(value)).toBe(expected)
  })

  test('handles negative values', () => {
    expect(new DecimalFormatter('unit', strict(2)).render(-1.5)).toBe('-1.5 unit')
  })
})

describe('SIFormatter', () => {
  const formatter = new SIFormatter('unit', strict(2))

  test('small value uses sub-unit prefix', () => {
    expect(formatter.render(0.0000123456789)).toBe('12.35 μunit')
  })

  test('large value uses k prefix', () => {
    expect(formatter.render(123456.789)).toBe('123.46 kunit')
  })

  test('large border (Python si-large-border): 999.999 rounds to 1000 unit', () => {
    expect(formatter.render(999.999)).toBe('1000 unit')
  })

  test('handles negative values', () => {
    expect(formatter.render(-12345)).toBe('-12.35 kunit')
  })
})

describe('IECFormatter', () => {
  const formatter = new IECFormatter('unit', strict(2))

  test('small value falls through unchanged', () => {
    expect(formatter.render(0.0000123456789)).toBe('0 unit')
  })

  test('large value uses Ki prefix', () => {
    expect(formatter.render(123456.789)).toBe('120.56 Kiunit')
  })

  test('large border (Python iec-large-border): 1023.999 rounds to 1024 unit', () => {
    expect(formatter.render(1023.999)).toBe('1024 unit')
  })

  test('handles negative values', () => {
    expect(formatter.render(-2048)).toBe('-2 Kiunit')
  })
})

describe('StandardScientificFormatter', () => {
  const formatter = new StandardScientificFormatter('unit', strict(2))

  test('small value', () => {
    expect(formatter.render(0.0000123456789)).toBe('1.23e-5 unit')
  })

  test('large value', () => {
    expect(formatter.render(123456.789)).toBe('1.23e+5 unit')
  })

  test('exact power of ten (small)', () => {
    expect(formatter.render(0.00001)).toBe('1e-5 unit')
  })

  test('exact power of ten (large)', () => {
    expect(formatter.render(100000.0)).toBe('1e+5 unit')
  })
})

describe('EngineeringScientificFormatter', () => {
  const formatter = new EngineeringScientificFormatter('unit', strict(2))

  test('small value', () => {
    expect(formatter.render(0.0000123456789)).toBe('12.35e-6 unit')
  })

  test('large value', () => {
    expect(formatter.render(123456.789)).toBe('123.46e+3 unit')
  })

  test('exact power of ten (small)', () => {
    expect(formatter.render(0.00001)).toBe('10e-6 unit')
  })

  test('exact power of ten (large 1e6)', () => {
    expect(formatter.render(1000000)).toBe('1e+6 unit')
  })

  test('exact power of ten (large 1e5)', () => {
    expect(formatter.render(100000)).toBe('100e+3 unit')
  })

  test('large multiple of 1e3', () => {
    expect(formatter.render(120000)).toBe('120e+3 unit')
  })
})

describe('TimeFormatter', () => {
  const formatter = new TimeFormatter('s', strict(2))

  test('microseconds', () => {
    expect(formatter.render(0.0000123456789)).toBe('12.35 μs')
  })

  test('seconds-and-minutes', () => {
    expect(formatter.render(137)).toBe('2 min 17 s')
  })

  test('hours-and-minutes', () => {
    expect(formatter.render(4312)).toBe('1 h 12 min')
  })

  test('days-and-hours', () => {
    expect(formatter.render(123456.789)).toBe('1 d 10 h')
  })

  test('rolls over to 24 h at day boundary', () => {
    expect(formatter.render(86399.999)).toBe('24 h')
  })

  test('exact one year', () => {
    expect(formatter.render(31536000)).toBe('1 y')
  })

  test('one and a half years uses banker rounding for days', () => {
    expect(formatter.render(47304000)).toBe('1 y 182 d')
  })

  test('ten years', () => {
    expect(formatter.render(315360000)).toBe('10 y')
  })

  test('handles negative values', () => {
    expect(formatter.render(-3600)).toBe('-1 h')
  })
})

describe('precision digits clamp', () => {
  test('negative digits do not throw', () => {
    expect(new DecimalFormatter('unit', { type: 'strict', digits: -1 }).render(1.5)).toBe('2 unit')
  })

  test('digits beyond toFixed range do not throw', () => {
    // toFixed throws RangeError for digits > 100; the clamp keeps us safe.
    expect(() =>
      new DecimalFormatter('unit', { type: 'strict', digits: 200 }).render(1.5)
    ).not.toThrow()
  })
})

describe('symbol with leading slash or percent', () => {
  test('decimal: no separator before /unit', () => {
    expect(new DecimalFormatter('/unit', strict(2)).render(2)).toBe('2/unit')
  })

  test('si: separator stays when an SI prefix is in front', () => {
    expect(new SIFormatter('/unit', strict(2)).render(2000)).toBe('2 k/unit')
  })

  test('decimal: no separator before %', () => {
    expect(new DecimalFormatter('%', strict(2)).render(50)).toBe('50%')
  })
})

describe('stringifySmallDecimalNumber', () => {
  // Mirrors test__stringify_small_decimal_number in
  // tests/unit/cmk/gui/test_unit_formatter.py. JS's String() produces
  // scientific notation only at a much smaller threshold than Python, so
  // none of the original Python fixtures actually exercise the e-notation
  // branch in JS — they all stringify to decimal natively. The cases below
  // pin that down; the trailing two cases drive the e-notation conversion
  // path explicitly.
  test.each<[number, string]>([
    [0.1023, '0.1023'],
    [0.01023, '0.01023'],
    [0.001023, '0.001023'],
    [0.0001023, '0.0001023'],
    [0.00001023, '0.00001023'],
    [0.000001023, '0.000001023'],
    // JS edge cases: String() switches to e-notation here.
    [1.023e-7, '0.0000001023'],
    [1.023e-9, '0.000000001023']
  ])('value=%s -> %s', (value, expected) => {
    expect(stringifySmallDecimalNumber(value)).toBe(expected)
  })
})

// Mirrors test_render_y_labels in tests/unit/cmk/gui/test_unit_formatter.py.
// All fixtures call render_y_labels with target_number_of_labels=5.
describe('renderYLabels', () => {
  type Case = {
    id: string
    formatter: () => NotationFormatter
    yRange: PositiveYRange | NegativeYRange
    expected: Label[]
  }
  const cases: Case[] = [
    {
      id: 'decimal-small',
      formatter: () => new DecimalFormatter('u', auto(2)),
      yRange: pos(0.0, 0.00123),
      expected: [
        { value: 0, text: '0' },
        { value: 0.0002, text: '0.0002 u' },
        { value: 0.0004, text: '0.0004 u' },
        { value: 0.0006000000000000001, text: '0.0006 u' },
        { value: 0.0008, text: '0.0008 u' },
        { value: 0.001, text: '0.001 u' },
        { value: 0.0012000000000000001, text: '0.0012 u' }
      ]
    },
    {
      id: 'decimal-large',
      formatter: () => new DecimalFormatter('u', auto(2)),
      yRange: pos(0.0, 123456.789),
      expected: [
        { value: 0, text: '0' },
        { value: 20000, text: `20${TS}000 u` },
        { value: 40000, text: `40${TS}000 u` },
        { value: 60000, text: `60${TS}000 u` },
        { value: 80000, text: `80${TS}000 u` },
        { value: 100000, text: `100${TS}000 u` },
        { value: 120000, text: `120${TS}000 u` }
      ]
    },
    {
      id: 'decimal-negative',
      formatter: () => new DecimalFormatter('u', auto(2)),
      yRange: neg(-11.19, -2.123),
      expected: [
        { value: -2, text: '-2 u' },
        { value: -4, text: '-4 u' },
        { value: -6, text: '-6 u' },
        { value: -8, text: '-8 u' },
        { value: -10, text: '-10 u' }
      ]
    },
    {
      id: 'si-small',
      formatter: () => new SIFormatter('u', auto(2)),
      yRange: pos(0.0, 0.00123),
      expected: [
        { value: 0, text: '0' },
        { value: 0.0002, text: '0.2 mu' },
        { value: 0.0004, text: '0.4 mu' },
        { value: 0.0006000000000000001, text: '0.6 mu' },
        { value: 0.0008, text: '0.8 mu' },
        { value: 0.001, text: '1 mu' },
        { value: 0.0012000000000000001, text: '1.2 mu' }
      ]
    },
    {
      id: 'si-large',
      formatter: () => new SIFormatter('u', auto(2)),
      yRange: pos(0.0, 123456.789),
      expected: [
        { value: 0, text: '0' },
        { value: 20000, text: '20 ku' },
        { value: 40000, text: '40 ku' },
        { value: 60000, text: '60 ku' },
        { value: 80000, text: '80 ku' },
        { value: 100000, text: '100 ku' },
        { value: 120000, text: '120 ku' }
      ]
    },
    {
      id: 'si-negative',
      formatter: () => new SIFormatter('u', auto(2)),
      yRange: neg(-1.12e5, -423),
      expected: [
        { value: 0, text: '0' },
        { value: -20000, text: '-20 ku' },
        { value: -40000, text: '-40 ku' },
        { value: -60000, text: '-60 ku' },
        { value: -80000, text: '-80 ku' },
        { value: -100000, text: '-100 ku' }
      ]
    },
    {
      id: 'iec-small',
      formatter: () => new IECFormatter('u', auto(2)),
      yRange: pos(0.0, 0.00123),
      expected: [
        { value: 0, text: '0' },
        { value: 0.0002, text: '0.0002 u' },
        { value: 0.0004, text: '0.0004 u' },
        { value: 0.0006000000000000001, text: '0.0006 u' },
        { value: 0.0008, text: '0.0008 u' },
        { value: 0.001, text: '0.001 u' },
        { value: 0.0012000000000000001, text: '0.0012 u' }
      ]
    },
    {
      id: 'iec-large',
      formatter: () => new IECFormatter('u', auto(2)),
      yRange: pos(0.0, 123456.789),
      expected: [
        { value: 0, text: '0' },
        { value: 16384, text: '16 Kiu' },
        { value: 32768, text: '32 Kiu' },
        { value: 49152, text: '48 Kiu' },
        { value: 65536, text: '64 Kiu' },
        { value: 81920, text: '80 Kiu' },
        { value: 98304, text: '96 Kiu' },
        { value: 114688, text: '112 Kiu' }
      ]
    },
    {
      id: 'iec-negative',
      formatter: () => new IECFormatter('u', auto(2)),
      yRange: neg(-0.144, -4.432e-4),
      expected: [
        { value: 0, text: '0' },
        { value: -0.02, text: '-0.02 u' },
        { value: -0.04, text: '-0.04 u' },
        { value: -0.06, text: '-0.06 u' },
        { value: -0.08, text: '-0.08 u' },
        { value: -0.1, text: '-0.1 u' },
        { value: -0.12, text: '-0.12 u' },
        { value: -0.14, text: '-0.14 u' }
      ]
    },
    {
      id: 'std-sci-small',
      formatter: () => new StandardScientificFormatter('u', auto(2)),
      yRange: pos(0.0, 0.00123),
      expected: [
        { value: 0, text: '0' },
        { value: 0.0002, text: '2e-4 u' },
        { value: 0.0004, text: '4e-4 u' },
        { value: 0.0006000000000000001, text: '6e-4 u' },
        { value: 0.0008, text: '8e-4 u' },
        { value: 0.001, text: '1e-3 u' },
        { value: 0.0012000000000000001, text: '1.2e-3 u' }
      ]
    },
    {
      id: 'std-sci-large',
      formatter: () => new StandardScientificFormatter('u', auto(2)),
      yRange: pos(0.0, 123456.789),
      expected: [
        { value: 0, text: '0' },
        { value: 20000, text: '2e+4 u' },
        { value: 40000, text: '4e+4 u' },
        { value: 60000, text: '6e+4 u' },
        { value: 80000, text: '8e+4 u' },
        { value: 100000, text: '1e+5 u' },
        { value: 120000, text: '1.2e+5 u' }
      ]
    },
    {
      id: 'std-sci-negative',
      formatter: () => new StandardScientificFormatter('u', auto(2)),
      yRange: neg(-5e10, -1e10),
      expected: [
        { value: -10000000000, text: '-1e+10 u' },
        { value: -20000000000, text: '-2e+10 u' },
        { value: -30000000000, text: '-3e+10 u' },
        { value: -40000000000, text: '-4e+10 u' },
        { value: -50000000000, text: '-5e+10 u' }
      ]
    },
    {
      id: 'eng-sci-small',
      formatter: () => new EngineeringScientificFormatter('u', auto(2)),
      yRange: pos(0.0, 0.00123),
      expected: [
        { value: 0, text: '0' },
        { value: 0.0002, text: '200e-6 u' },
        { value: 0.0004, text: '400e-6 u' },
        { value: 0.0006000000000000001, text: '600e-6 u' },
        { value: 0.0008, text: '800e-6 u' },
        { value: 0.001, text: '1e-3 u' },
        { value: 0.0012000000000000001, text: '1.2e-3 u' }
      ]
    },
    {
      id: 'eng-sci-large',
      formatter: () => new EngineeringScientificFormatter('u', auto(2)),
      yRange: pos(0.0, 123456.789),
      expected: [
        { value: 0, text: '0' },
        { value: 20000, text: '20e+3 u' },
        { value: 40000, text: '40e+3 u' },
        { value: 60000, text: '60e+3 u' },
        { value: 80000, text: '80e+3 u' },
        { value: 100000, text: '100e+3 u' },
        { value: 120000, text: '120e+3 u' }
      ]
    },
    {
      id: 'eng-sci-negative',
      formatter: () => new EngineeringScientificFormatter('u', auto(2)),
      yRange: neg(-5e10, -1e2),
      expected: [
        { value: 0, text: '0' },
        { value: -10000000000, text: '-10e+9 u' },
        { value: -20000000000, text: '-20e+9 u' },
        { value: -30000000000, text: '-30e+9 u' },
        { value: -40000000000, text: '-40e+9 u' },
        { value: -50000000000, text: '-50e+9 u' }
      ]
    },
    {
      id: 'time-small',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: pos(0.0, 0.00123),
      expected: [
        { value: 0, text: '0' },
        { value: 0.0002, text: '0.2 ms' },
        { value: 0.0004, text: '0.4 ms' },
        { value: 0.0006000000000000001, text: '0.6 ms' },
        { value: 0.0008, text: '0.8 ms' },
        { value: 0.001, text: '1 ms' },
        { value: 0.0012000000000000001, text: '1.2 ms' }
      ]
    },
    {
      id: 'time-large',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: pos(0.0, 123456.789),
      expected: [
        { value: 0, text: '0' },
        { value: 21600, text: '6 h' },
        { value: 43200, text: '12 h' },
        { value: 64800, text: '18 h' },
        { value: 86400, text: '24 h' },
        { value: 108000, text: '30 h' }
      ]
    },
    {
      id: 'time->year',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: pos(0, 31536001),
      expected: [
        { value: 0, text: '0' },
        { value: 4320000, text: '50 d' },
        { value: 8640000, text: '100 d' },
        { value: 12960000, text: '150 d' },
        { value: 17280000, text: '200 d' },
        { value: 21600000, text: '250 d' },
        { value: 25920000, text: '300 d' },
        { value: 30240000, text: '350 d' }
      ]
    },
    {
      id: 'time-half-year',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: pos(0.0, 15552000.123),
      expected: [
        { value: 0, text: '0' },
        { value: 4320000, text: '50 d' },
        { value: 8640000, text: '100 d' },
        { value: 12960000, text: '150 d' }
      ]
    },
    {
      id: 'time-three-years',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: pos(0, 94608000),
      expected: [
        { value: 0, text: '0' },
        { value: 31536000, text: '1 y' },
        { value: 63072000, text: '2 y' },
        { value: 94608000, text: '3 y' }
      ]
    },
    {
      id: 'time-ten-years',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: pos(0, 315360000),
      expected: [
        { value: 0, text: '0' },
        { value: 63072000, text: '2 y' },
        { value: 126144000, text: '4 y' },
        { value: 189216000, text: '6 y' },
        { value: 252288000, text: '8 y' },
        { value: 315360000, text: '10 y' }
      ]
    },
    {
      id: 'time-negative-small',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: neg(-10.123, -5.11),
      expected: [
        { value: -5, text: '-5 s' },
        { value: -6, text: '-6 s' },
        { value: -7, text: '-7 s' },
        { value: -8, text: '-8 s' },
        { value: -9, text: '-9 s' },
        { value: -10, text: '-10 s' }
      ]
    },
    {
      id: 'time-negative-large',
      formatter: () => new TimeFormatter('s', auto(2)),
      yRange: neg(-25552000.123, -15552000.123),
      expected: [
        { value: -15552000, text: '-180 d' },
        { value: -17280000, text: '-200 d' },
        { value: -19008000, text: '-220 d' },
        { value: -20736000, text: '-240 d' },
        { value: -22464000, text: '-260 d' },
        { value: -24192000, text: '-280 d' }
      ]
    }
  ]

  test.each(cases.map((c) => [c.id, c] as const))('%s', (_, c) => {
    expect(c.formatter().renderYLabels(c.yRange, 5)).toEqual(c.expected)
  })
})

// Mirrors test_decimal_render_y_labels_with_min_y in
// tests/unit/cmk/gui/test_unit_formatter.py.
describe('DecimalFormatter renderYLabels with min y', () => {
  test.each<[string, PositiveYRange | NegativeYRange, Label[]]>([
    [
      'decimal-small',
      pos(0.00123, 0.00456),
      [
        { value: 0, text: '0' },
        { value: 0.001, text: '0.001 u' },
        { value: 0.002, text: '0.002 u' },
        { value: 0.003, text: '0.003 u' },
        { value: 0.004, text: '0.004 u' }
      ]
    ],
    [
      'decimal-large',
      pos(123.456, 456.789),
      [
        { value: 100, text: '100 u' },
        { value: 150, text: '150 u' },
        { value: 200, text: '200 u' },
        { value: 250, text: '250 u' },
        { value: 300, text: '300 u' },
        { value: 350, text: '350 u' },
        { value: 400, text: '400 u' },
        { value: 450, text: '450 u' }
      ]
    ],
    [
      'decimal-negative',
      neg(-456.789, -123.456),
      [
        { value: -100, text: '-100 u' },
        { value: -150, text: '-150 u' },
        { value: -200, text: '-200 u' },
        { value: -250, text: '-250 u' },
        { value: -300, text: '-300 u' },
        { value: -350, text: '-350 u' },
        { value: -400, text: '-400 u' },
        { value: -450, text: '-450 u' }
      ]
    ]
  ])('%s', (_, yRange, expected) => {
    expect(new DecimalFormatter('u', auto(2)).renderYLabels(yRange, 5)).toEqual(expected)
  })
})

// Mirrors test_render_y_labels_small_range_large_offset in
// tests/unit/cmk/gui/test_unit_formatter.py.
describe('renderYLabels small range large offset', () => {
  test('TimeFormatter with use_max_digits_for_labels=true', () => {
    const formatter = new TimeFormatter('s', auto(2), true)
    expect(formatter.renderYLabels(pos(1.0011975, 1.2515224999999999), 5.0)).toEqual([
      { value: 0.9500000000000001, text: '0.95 s' },
      { value: 1.0, text: '1 s' },
      { value: 1.05, text: '1.05 s' },
      { value: 1.1, text: '1.1 s' },
      { value: 1.1500000000000001, text: '1.15 s' },
      { value: 1.2000000000000002, text: '1.2 s' },
      { value: 1.25, text: '1.25 s' }
    ])
  })
})
