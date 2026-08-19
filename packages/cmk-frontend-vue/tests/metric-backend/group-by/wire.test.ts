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

type Stage = Aggregator['stages'][number]

const MAIN = model({
  function: 'avg',
  keys: [
    { id: 'a', attributeKind: 'resource', attributeKey: 'service.name' },
    { id: 'b', attributeKind: 'resource', attributeKey: 'cloud.region' }
  ]
})
const HISTOGRAM = model({
  function: 'percentile',
  keys: [{ id: 'a', attributeKind: 'resource', attributeKey: 'service.name' }]
})

const THEN_STEPS = [
  step({
    function: 'sum',
    keys: [{ id: 'c', attributeKind: 'resource', attributeKey: 'cloud.region' }]
  }),
  step({ function: 'count', keys: [] })
]
const SUM_BY_REGION_STAGE: Stage = {
  aggregate_by: [{ kind: 'resource', name: 'cloud.region' }],
  aggregation_fn: { type: 'scalar', name: 'sum' }
}
const COUNT_STAGE: Stage = { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'count' } }

test.each<[string, GroupByModel, Stage[]]>([
  [
    'a scalar float grouping leads with its own stage',
    MAIN,
    [
      {
        aggregate_by: [
          { kind: 'resource', name: 'service.name' },
          { kind: 'resource', name: 'cloud.region' }
        ],
        aggregation_fn: { type: 'scalar', name: 'avg' }
      }
    ]
  ],
  [
    'a scalar grouping over everything leads with an empty stage',
    model({ function: 'avg', keys: [] }),
    [{ aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'avg' } }]
  ],
  [
    'a histogram grouping omits the leading stage, its group-by riding the consolidation',
    HISTOGRAM,
    []
  ]
])('serializing then steps: %s', (_scenario, groupBy, leadingStages) => {
  expect(aggregatorFromGroupBy(groupBy, THEN_STEPS)).toEqual<Aggregator>({
    stages: [...leadingStages, SUM_BY_REGION_STAGE, COUNT_STAGE]
  })
})

test.each<[string, GroupByModel, AggregationStep[]]>([
  ['"no grouping" drops any then steps', model({ function: 'none' }), [step({ function: 'sum' })]],
  ['a histogram grouping has no then steps', HISTOGRAM, []]
])('%s, so it serializes to no aggregator', (_scenario, groupBy, thenSteps) => {
  expect(aggregatorFromGroupBy(groupBy, thenSteps)).toBeUndefined()
})

test.each<[string, GroupByModel]>([
  ['a scalar float grouping', MAIN],
  ['a histogram grouping', HISTOGRAM]
])('then steps round-trip through %s, minting fresh ids', (_scenario, groupBy) => {
  const steps = [
    step({
      function: 'sum',
      keys: [{ id: 'c', attributeKind: 'data_point', attributeKey: 'http.route' }]
    }),
    step({ function: 'count', keys: [] })
  ]
  const aggregator = aggregatorFromGroupBy(groupBy, steps)

  let next = 0
  const back = aggregatorToThenSteps(aggregator, groupBy, () => `id${next++}`)
  expect(back).toEqual<AggregationStep[]>([
    {
      id: 'id0',
      function: 'sum',
      keys: [{ id: 'id1', attributeKind: 'data_point', attributeKey: 'http.route' }]
    },
    { id: 'id2', function: 'count', keys: [] }
  ])
})

test('the first stage is the main group-by, so a single-stage aggregator has no then steps', () => {
  expect(aggregatorToThenSteps(floatGroupByToAggregator(MAIN), MAIN)).toEqual([])
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

  const steps = aggregatorToThenSteps(aggregator, MAIN, () => 'x')
  expect(steps).toHaveLength(1)
  expect(steps[0]!.function).toBe('sum')
})
