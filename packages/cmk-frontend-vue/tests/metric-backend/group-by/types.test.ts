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
  functionsForInputType
} from '@/metric-backend/group-by/types'
import type { GroupByFunction, GroupByInputType } from '@/metric-backend/group-by/types'

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
