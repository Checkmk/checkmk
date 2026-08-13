/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'

import type { AggregationStep, FloatFunction, GroupByModel } from '@/metric-backend/group-by/types'
import {
  aggregatorFromGroupBy,
  aggregatorToFloatGroupBy,
  aggregatorToThenSteps,
  floatGroupByToAggregator
} from '@/metric-backend/group-by/wire'

function model(overrides: Partial<GroupByModel> = {}): GroupByModel {
  return { function: 'sum', params: {}, keys: [], ...overrides }
}

function step(overrides: Partial<AggregationStep> = {}): AggregationStep {
  return { id: 's', function: 'sum', keys: [], ...overrides }
}

const SCALAR_FUNCTIONS: Exclude<FloatFunction, 'none'>[] = ['avg', 'min', 'max', 'sum', 'count']

test.each(SCALAR_FUNCTIONS)(
  'round-trips the %s function and its keys through the aggregator',
  (fn) => {
    const groupBy = model({
      function: fn,
      keys: [
        { id: 'a', attributeKind: 'resource', attributeKey: 'service.name' },
        { id: 'b', attributeKind: 'scope', attributeKey: 'scope.name' }
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
      { id: 'k0', attributeKind: 'resource', attributeKey: 'service.name' },
      { id: 'k1', attributeKind: 'scope', attributeKey: 'scope.name' }
    ])
  }
)

test('the "none" function produces no aggregator', () => {
  expect(floatGroupByToAggregator(model({ function: 'none' }))).toBeUndefined()
})

test('a scalar function with no valid keys aggregates everything (an empty aggregate_by)', () => {
  expect(
    floatGroupByToAggregator(
      model({ function: 'sum', keys: [{ id: 'a', attributeKind: 'resource', attributeKey: '' }] })
    )
  ).toEqual<Aggregator>({
    stages: [{ aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'sum' } }]
  })
})

test('invalid keys (no key or no kind) are dropped while valid ones survive', () => {
  const aggregator = floatGroupByToAggregator(
    model({
      function: 'avg',
      keys: [
        { id: 'a', attributeKind: 'resource', attributeKey: '' },
        { id: 'b', attributeKind: null, attributeKey: 'unresolved.attr' },
        { id: 'c', attributeKind: 'data_point', attributeKey: 'http.method' }
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

const MAIN = model({
  function: 'avg',
  keys: [
    { id: 'a', attributeKind: 'resource', attributeKey: 'service.name' },
    { id: 'b', attributeKind: 'resource', attributeKey: 'cloud.region' }
  ]
})

test('a main group-by and its then steps serialize to one stage per step, in order', () => {
  const aggregator = aggregatorFromGroupBy(MAIN, [
    step({
      function: 'sum',
      keys: [{ id: 'c', attributeKind: 'resource', attributeKey: 'cloud.region' }]
    }),
    step({ function: 'count', keys: [] })
  ])

  expect(aggregator).toEqual<Aggregator>({
    stages: [
      {
        aggregate_by: [
          { kind: 'resource', name: 'service.name' },
          { kind: 'resource', name: 'cloud.region' }
        ],
        aggregation_fn: { type: 'scalar', name: 'avg' }
      },
      {
        aggregate_by: [{ kind: 'resource', name: 'cloud.region' }],
        aggregation_fn: { type: 'scalar', name: 'sum' }
      },
      { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'count' } }
    ]
  })
})

test('then steps round-trip through the aggregator, minting fresh ids', () => {
  const steps = [
    step({
      function: 'sum',
      keys: [{ id: 'c', attributeKind: 'data_point', attributeKey: 'http.route' }]
    }),
    step({ function: 'count', keys: [] })
  ]
  const aggregator = aggregatorFromGroupBy(MAIN, steps)

  let next = 0
  const back = aggregatorToThenSteps(aggregator, () => `id${next++}`)
  expect(back).toEqual<AggregationStep[]>([
    {
      id: 'id0',
      function: 'sum',
      keys: [{ id: 'id1', attributeKind: 'data_point', attributeKey: 'http.route' }]
    },
    { id: 'id2', function: 'count', keys: [] }
  ])
})

test('then steps are dropped when the main group-by is "no grouping"', () => {
  expect(
    aggregatorFromGroupBy(model({ function: 'none' }), [step({ function: 'sum' })])
  ).toBeUndefined()
})

test('a scalar main over everything keeps its then steps, anchored by an empty first stage', () => {
  expect(
    aggregatorFromGroupBy(model({ function: 'avg', keys: [] }), [step({ function: 'sum' })])
  ).toEqual<Aggregator>({
    stages: [
      { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'avg' } },
      { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'sum' } }
    ]
  })
})

test('the first stage is the main group-by, so a single-stage aggregator has no then steps', () => {
  expect(aggregatorToThenSteps(floatGroupByToAggregator(MAIN))).toEqual([])
})

test('a non-scalar stage stops the then-step chain', () => {
  const aggregator = {
    stages: [
      { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'avg' } },
      {
        aggregate_by: [{ kind: 'resource', name: 'cloud.region' }],
        aggregation_fn: { type: 'scalar', name: 'sum' }
      },
      { aggregate_by: [], aggregation_fn: { type: 'percentile', quantile: 0.9 } },
      { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'count' } }
    ]
  } as unknown as Aggregator

  const steps = aggregatorToThenSteps(aggregator, () => 'x')
  expect(steps).toHaveLength(1)
  expect(steps[0]!.function).toBe('sum')
})
