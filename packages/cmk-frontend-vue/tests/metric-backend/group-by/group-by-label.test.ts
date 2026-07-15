/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { clauseSummary, functionLabel } from '@/metric-backend/group-by/group-by-label'
import type { GroupByModel } from '@/metric-backend/group-by/types'

test('grouping functions read as "<function> by", with "no grouping" for the inert option', () => {
  expect(functionLabel('none')).toBe('no grouping')
  expect(functionLabel('avg')).toBe('avg by')
  expect(functionLabel('percentile')).toBe('percentile by')
  expect(functionLabel('fraction_between')).toBe('fraction between by')
})

test.each<[string, GroupByModel, string]>([
  ['inert', { function: 'none', params: {}, keys: [] }, 'no grouping'],
  ['active without keys', { function: 'avg', params: {}, keys: [] }, 'avg by everything'],
  [
    'active with keys',
    {
      function: 'avg',
      params: {},
      keys: [
        { id: '1', level: 'resource', key: 'service.name' },
        { id: '2', level: 'datapoint', key: 'http.route' }
      ]
    },
    'avg by [Resource] service.name, [Data point] http.route'
  ]
])('the clause summary for an %s clause', (_name, model, expected) => {
  expect(clauseSummary(model)).toBe(expected)
})
