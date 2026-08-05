/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  asTimeRangeValue,
  defaultTimeFilter,
  hasNonDefaultTime,
  withDefaultTime,
  withoutDefaultTime
} from '@/network-flow/flow-explorer/filters/timeRange'

test.each([
  [86400, { from: '1', range: '86400' }],
  [172800, { from: '2', range: '86400' }],
  [3600, { from: '1', range: '3600' }],
  [90000, { from: '25', range: '3600' }],
  [1800, { from: '30', range: '60' }],
  [90, { from: '90', range: '1' }]
])('%i seconds reads as the largest whole unit', (seconds, expected) => {
  expect(asTimeRangeValue(seconds)).toEqual(expected)
})

test('the split always multiplies back to the same duration', () => {
  for (const seconds of [1, 59, 60, 3599, 3600, 86399, 86400, 604800]) {
    const { from, range } = asTimeRangeValue(seconds)
    expect(Number(from) * Number(range)).toBe(seconds)
  }
})

test('a context without a time range gets the default put back', () => {
  expect(
    withDefaultTime({ network_flow_source: { network_flow_source_value: 'a' } }, 86400)
  ).toEqual({
    network_flow_source: { network_flow_source_value: 'a' },
    ...defaultTimeFilter(86400)
  })
})

test('an existing time range is left alone', () => {
  const context = defaultTimeFilter(3600)
  expect(withDefaultTime(context, 86400)).toBe(context)
})

test('only a time range off the default counts as filtered', () => {
  expect(hasNonDefaultTime(defaultTimeFilter(86400), 86400)).toBe(false)
  expect(hasNonDefaultTime(defaultTimeFilter(3600), 86400)).toBe(true)
  expect(hasNonDefaultTime({}, 86400)).toBe(false)
})

test('a default time range is left out of the URL', () => {
  expect(withoutDefaultTime(defaultTimeFilter(86400), 86400)).toEqual({})
  expect(
    withoutDefaultTime(
      { ...defaultTimeFilter(86400), network_flow_source: { network_flow_source_value: 'a' } },
      86400
    )
  ).toEqual({ network_flow_source: { network_flow_source_value: 'a' } })
})

test('a time range off the default stays in the URL', () => {
  const context = defaultTimeFilter(3600)
  expect(withoutDefaultTime(context, 86400)).toBe(context)
})
