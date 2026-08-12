/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'

import type { FloatFunction, GroupByModel } from '@/metric-backend/group-by/types'
import { aggregatorToFloatGroupBy, floatGroupByToAggregator } from '@/metric-backend/group-by/wire'

function model(overrides: Partial<GroupByModel> = {}): GroupByModel {
  return { function: 'sum', params: {}, keys: [], ...overrides }
}

const SCALAR_FUNCTIONS: Exclude<FloatFunction, 'none'>[] = ['avg', 'min', 'max', 'sum', 'count']

test.each(SCALAR_FUNCTIONS)(
  'round-trips the %s function and its keys through the aggregator',
  (fn) => {
    const groupBy = model({
      function: fn,
      keys: [
        { id: 'a', attributeKind: 'resource', key: 'service.name' },
        { id: 'b', attributeKind: 'scope', key: 'scope.name' }
      ]
    })

    const aggregator = floatGroupByToAggregator(groupBy)

    expect(aggregator).toEqual<Aggregator>({
      stages: [
        {
          aggregate_by: [
            { kind: 'resource', name: 'service.name' },
            { kind: 'scope', name: 'scope.name' }
          ],
          aggregation_fn: { type: 'scalar', name: fn }
        }
      ]
    })

    let next = 0
    const back = aggregatorToFloatGroupBy(aggregator, () => `k${next++}`)
    expect(back.function).toBe(fn)
    expect(back.params).toEqual({})
    expect(back.keys).toEqual([
      { id: 'k0', attributeKind: 'resource', key: 'service.name' },
      { id: 'k1', attributeKind: 'scope', key: 'scope.name' }
    ])
  }
)

test('the "none" function produces no aggregator', () => {
  expect(floatGroupByToAggregator(model({ function: 'none' }))).toBeUndefined()
})

test('a function with no valid keys produces no aggregator', () => {
  expect(
    floatGroupByToAggregator(model({ keys: [{ id: 'a', attributeKind: 'resource', key: '' }] }))
  ).toBeUndefined()
})

test('invalid (empty) keys are dropped while valid ones survive', () => {
  const aggregator = floatGroupByToAggregator(
    model({
      function: 'avg',
      keys: [
        { id: 'a', attributeKind: 'resource', key: '' },
        { id: 'b', attributeKind: 'data_point', key: 'http.method' }
      ]
    })
  )
  expect(aggregator?.stages[0]?.aggregate_by).toEqual([{ kind: 'data_point', name: 'http.method' }])
})

// Deliberately out of schema: the wire type only admits scalar functions, but stored JSON is
// unvalidated at this boundary, so the reader must degrade gracefully.
const HISTOGRAM_AGGREGATOR = {
  stages: [
    {
      aggregate_by: [{ kind: 'resource', name: 'service.name' }],
      aggregation_fn: { type: 'percentile', quantile: 0.95 }
    }
  ]
} as unknown as Aggregator

test.each<[string, Aggregator | undefined]>([
  ['an absent', undefined],
  ['a non-scalar (histogram)', HISTOGRAM_AGGREGATOR]
])('%s aggregator reads back as "no grouping"', (_id, aggregator) => {
  expect(aggregatorToFloatGroupBy(aggregator)).toEqual({ function: 'none', params: {}, keys: [] })
})
