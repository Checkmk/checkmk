/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { shallowRef } from 'vue'

import { CELL_PADDING } from '@/monitoring/shared/components/MonitoringTableContext'
import {
  type TextWidth,
  timestampColumnsAsShown,
  useTimestampColumnWidth
} from '@/monitoring/shared/components/timestampColumns'
import { formatDisplayTimestamp } from '@/monitoring/shared/formatTimestamp'
import type { DateFormatId, DisplayOptions, TimestampFormatId } from '@/monitoring/shared/types'

interface Row {
  last_check?: number | null
}

const NOW = 1_790_000_000
const MINUTE = 60
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR
const YEAR = 365 * DAY

// A proportional font, where `1` is the narrowest digit and `4` the widest.
const GLYPH_WIDTHS: Record<string, number> = { '1': 3, '4': 8, m: 10, ' ': 2, '.': 2, ':': 2 }

const proportionalWidth: TextWidth = (text) =>
  [...text].reduce((sum, glyph) => sum + (GLYPH_WIDTHS[glyph] ?? 6), 0)

const TIMESTAMP_FORMATS: TimestampFormatId[] = ['mixed', 'abs', 'rel', 'both', 'epoch']
const DATE_FORMATS: DateFormatId[] = ['%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y', '%d.%m.', '%m/%d']

// Ages at the edges where each unit renders its longest text.
const AGES = [
  0.0004,
  0.9994,
  0.9996,
  9.994,
  9.996,
  59.96,
  239.9,
  359.9 * MINUTE,
  47.9 * HOUR,
  5.94 * DAY,
  998.6 * DAY,
  9.96 * YEAR,
  56 * YEAR
]

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW * 1000)
})

afterEach(() => {
  vi.useRealTimers()
})

function columnWidth(options: DisplayOptions, textWidth: TextWidth = proportionalWidth): number {
  return useTimestampColumnWidth(() => options, shallowRef(textWidth)).value!
}

test.each(
  TIMESTAMP_FORMATS.flatMap((timestampFormat) =>
    DATE_FORMATS.map((dateFormat) => ({ timestampFormat, dateFormat }))
  )
)('the column fits every text $timestampFormat with $dateFormat renders', (options) => {
  const width = columnWidth(options)

  for (const timestamp of AGES.map((age) => NOW - age)) {
    const text = formatDisplayTimestamp(timestamp, options)
    expect(proportionalWidth(text) + CELL_PADDING, text).toBeLessThanOrEqual(width)
  }
})

test('the column fits ten of the widest digit for unix timestamps', () => {
  expect(columnWidth({ dateFormat: '%Y-%m-%d', timestampFormat: 'epoch' })).toBe(
    10 * 8 + 1 + CELL_PADDING
  )
})

test('the column follows the font once it changes', () => {
  const textWidth = shallowRef<TextWidth>(() => 5)
  const width = useTimestampColumnWidth(
    () => ({ dateFormat: '%Y-%m-%d', timestampFormat: 'epoch' }),
    textWidth
  )
  expect(width.value).toBe(5 + 1 + CELL_PADDING)

  textWidth.value = () => 7

  expect(width.value).toBe(7 + 1 + CELL_PADDING)
})

test('the column has no width while text cannot be measured', () => {
  const width = useTimestampColumnWidth(
    () => ({ dateFormat: '%Y-%m-%d', timestampFormat: 'both' }),
    shallowRef(null)
  )

  expect(width.value).toBeNull()
})

const CHECK_AGE: ColumnDef<Row> = {
  accessorKey: 'last_check',
  minSize: 120,
  maxSize: 200,
  meta: { justify: 'right', filter: { type: 'date-time-range', field: 'last_check' } }
}

test('a timestamp column is fixed at its width and fits its header', () => {
  expect(timestampColumnsAsShown<Row>([CHECK_AGE], 'abs', 90)[0]).toMatchObject({
    minSize: 90,
    maxSize: 90,
    meta: { justify: 'right', fitHeader: true }
  })
})

test('a timestamp column without a width keeps its own sizes', () => {
  expect(timestampColumnsAsShown<Row>([CHECK_AGE], 'abs', null)[0]).toMatchObject({
    minSize: 120,
    maxSize: 200,
    meta: { justify: 'right', fitHeader: true }
  })
})

test.each<TimestampFormatId>(['rel', 'mixed', 'both'])(
  'a timestamp shown as an age (%s) is filtered by duration',
  (format) => {
    expect(timestampColumnsAsShown<Row>([CHECK_AGE], format, 90)[0]!.meta?.filter).toEqual({
      type: 'duration',
      field: 'last_check'
    })
  }
)

test.each<TimestampFormatId>(['abs', 'epoch'])(
  'a timestamp shown as a point in time (%s) keeps the date-time range filter',
  (format) => {
    expect(timestampColumnsAsShown<Row>([CHECK_AGE], format, 90)[0]!.meta?.filter).toEqual({
      type: 'date-time-range',
      field: 'last_check'
    })
  }
)

test('a column that is no timestamp is left as it is', () => {
  const summary: ColumnDef<Row> = {
    accessorKey: 'summary',
    minSize: 200,
    meta: { filter: { type: 'string-input', field: 'summary' } }
  }

  expect(timestampColumnsAsShown<Row>([summary], 'rel', 90)[0]).toBe(summary)
})
