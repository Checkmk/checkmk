/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  FLOAT_FUNCTIONS,
  HISTOGRAM_FUNCTIONS,
  defaultFunction,
  functionParamKind,
  functionsForInputType,
  isKeyValid,
  thenStepsAllowed
} from '@/metric-backend/group-by/types'
import type {
  GroupByFunction,
  GroupByInputType,
  GroupByModel,
  GroupKey
} from '@/metric-backend/group-by/types'

function model(overrides: Partial<GroupByModel> = {}): GroupByModel {
  return { function: 'avg', params: {}, keys: [], ...overrides }
}

test.each<[GroupByInputType, readonly GroupByFunction[]]>([
  ['float', FLOAT_FUNCTIONS],
  ['histogram', HISTOGRAM_FUNCTIONS]
])('%s input offers its catalog in order and defaults to the first', (type, expected) => {
  expect(functionsForInputType(type)).toEqual(expected)
  expect(defaultFunction(type)).toBe(expected[0])
})

test('parameter kind maps histogram functions to their inputs, aggregations to none', () => {
  expect(functionParamKind('percentile')).toBe('quantile')
  expect(functionParamKind('fraction_below')).toBe('fraction_below')
  expect(functionParamKind('fraction_between')).toBe('fraction_between')
  expect(functionParamKind('avg')).toBe('none')
})

test.each<[string, GroupKey, boolean]>([
  ['both set', { id: '1', attributeKind: 'resource', attributeKey: 'service.name' }, true],
  ['no key', { id: '1', attributeKind: 'resource', attributeKey: '' }, false],
  ['no kind', { id: '1', attributeKind: null, attributeKey: 'service.name' }, false],
  ['neither', { id: '1', attributeKind: null, attributeKey: '' }, false]
])('a key is valid only with both a key and a kind (%s)', (_name, key, expected) => {
  expect(isKeyValid(key)).toBe(expected)
})

test.each<[string, GroupByInputType, GroupByModel, boolean]>([
  [
    'a scalar float grouping',
    'float',
    model({ function: 'avg', keys: [{ id: '1', attributeKind: 'resource', attributeKey: 'x' }] }),
    true
  ],
  ['the same grouping over everything', 'float', model({ function: 'avg', keys: [] }), true],
  ['"no grouping"', 'float', model({ function: 'none' }), false],
  ['a histogram function', 'histogram', model({ function: 'percentile' }), false]
])('then steps are allowed for %s: %s', (_scenario, inputType, groupBy, expected) => {
  expect(thenStepsAllowed(inputType, groupBy)).toBe(expected)
})
