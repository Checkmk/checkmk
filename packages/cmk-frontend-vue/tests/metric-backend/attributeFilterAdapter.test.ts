/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'

import type {
  AttributeFilterModel,
  AttributeKind,
  Condition,
  Operator
} from '@/metric-backend/attribute-filter/types'
import {
  type ThreeLists,
  buildAutocompleteContext,
  fromAttributeFilter,
  fromModel,
  toAttributeFilter
} from '@/metric-backend/attributeFilterAdapter'

let counter = 0
function newId(): string {
  counter += 1
  return `id-${counter}`
}

function group(...conditions: Condition[]): AttributeFilterModel {
  return [{ id: 'g', conditions }]
}

const lists: ThreeLists = {
  resource: [{ key: 'service.name', value: 'frontend' }],
  scope: [{ key: 'otel.library.name', value: 'http' }],
  data_point: [
    { key: 'http.method', value: 'GET' },
    { key: 'http.route', value: '/api' }
  ]
}

function modelFromLists(source: ThreeLists): AttributeFilterModel {
  const conditions: Condition[] = (['resource', 'scope', 'data_point'] as const).flatMap((kind) =>
    source[kind].map((attr) => ({
      id: newId(),
      attributeKind: kind,
      key: attr.key,
      operator: 'eq' as const,
      value: attr.value
    }))
  )
  return conditions.length === 0 ? [] : [{ id: newId(), conditions }]
}

describe('fromModel', () => {
  test('buckets conditions back into the three lists by attributeKind', () => {
    expect(fromModel(modelFromLists(lists))).toEqual(lists)
  })

  test('drops conditions with no attributeKind or empty key (pills still being created)', () => {
    const model = group(
      { id: 'a', attributeKind: null, key: '', operator: 'eq', value: '' },
      { id: 'b', attributeKind: 'resource', key: '', operator: 'eq', value: 'x' },
      { id: 'c', attributeKind: 'scope', key: 'otel.library.name', operator: 'eq', value: 'http' }
    )

    expect(fromModel(model)).toEqual({
      resource: [],
      scope: [{ key: 'otel.library.name', value: 'http' }],
      data_point: []
    })
  })
})

describe('buildAutocompleteContext', () => {
  test('encodes the model as a recursive filter, dropping the excluded pill, plus the options', () => {
    const model = group(
      { id: 'self', attributeKind: 'data_point', key: 'http.method', operator: 'eq', value: 'GET' },
      { id: 'other', attributeKind: 'data_point', key: 'http.route', operator: 'eq', value: '/api' }
    )

    expect(
      buildAutocompleteContext(model, {
        metricName: 'http_requests',
        staticResourceAttributeKeys: ['service.name'],
        attributeKey: 'http.method',
        excludeId: 'self'
      })
    ).toEqual({
      metric_name: 'http_requests',
      static_resource_attribute_keys: ['service.name'],
      attribute_key: 'http.method',
      attribute_filter: {
        type: 'equals',
        key: { kind: 'data_point', name: 'http.route' },
        value: '/api'
      }
    })
  })
})

describe('toAttributeFilter', () => {
  test('encodes one AND group', () => {
    expect(toAttributeFilter(modelFromLists(lists))).toEqual({
      type: 'and',
      conjuncts: [
        { type: 'equals', key: { kind: 'resource', name: 'service.name' }, value: 'frontend' },
        { type: 'equals', key: { kind: 'scope', name: 'otel.library.name' }, value: 'http' },
        { type: 'equals', key: { kind: 'data_point', name: 'http.method' }, value: 'GET' },
        { type: 'equals', key: { kind: 'data_point', name: 'http.route' }, value: '/api' }
      ]
    })
  })

  test('encodes multiple groups as an OR of ANDs', () => {
    const model: AttributeFilterModel = [
      {
        id: 'g1',
        conditions: [
          { id: 'a', attributeKind: 'resource', key: 'k1', operator: 'eq', value: 'v1' },
          { id: 'b', attributeKind: 'scope', key: 'k2', operator: 'eq', value: 'v2' }
        ]
      },
      {
        id: 'g2',
        conditions: [{ id: 'c', attributeKind: 'resource', key: 'k3', operator: 'eq', value: 'v3' }]
      }
    ]

    expect(toAttributeFilter(model)).toEqual({
      type: 'or',
      disjuncts: [
        {
          type: 'and',
          conjuncts: [
            { type: 'equals', key: { kind: 'resource', name: 'k1' }, value: 'v1' },
            { type: 'equals', key: { kind: 'scope', name: 'k2' }, value: 'v2' }
          ]
        },
        { type: 'equals', key: { kind: 'resource', name: 'k3' }, value: 'v3' }
      ]
    })
  })

  test('encodes the exists operator without a value', () => {
    const model = group({
      id: 'a',
      attributeKind: 'scope',
      key: 'scope.name',
      operator: 'exists',
      value: ''
    })

    expect(toAttributeFilter(model)).toEqual({
      type: 'exists',
      key: { kind: 'scope', name: 'scope.name' }
    })
  })

  test.each<[Operator, string, AttributeFilter]>([
    [
      'not_exists',
      '',
      { type: 'not', condition: { type: 'exists', key: { kind: 'scope', name: 'a' } } }
    ],
    [
      'neq',
      'v',
      { type: 'not', condition: { type: 'equals', key: { kind: 'scope', name: 'a' }, value: 'v' } }
    ],
    [
      'not_contains',
      'v',
      {
        type: 'not',
        condition: { type: 'contains', key: { kind: 'scope', name: 'a' }, value: 'v' }
      }
    ],
    [
      'not_starts_with',
      'v',
      {
        type: 'not',
        condition: { type: 'starts_with', key: { kind: 'scope', name: 'a' }, value: 'v' }
      }
    ],
    [
      'not_ends_with',
      'v',
      {
        type: 'not',
        condition: { type: 'ends_with', key: { kind: 'scope', name: 'a' }, value: 'v' }
      }
    ],
    [
      'not_regex',
      'v.*',
      {
        type: 'not',
        condition: { type: 'regex', key: { kind: 'scope', name: 'a' }, value: 'v.*' }
      }
    ]
  ])('encodes the negated operator %s as a not(...) node', (operator, value, expected) => {
    expect(
      toAttributeFilter(group({ id: 'a', attributeKind: 'scope', key: 'a', operator, value }))
    ).toEqual(expected)
  })

  test('drops incomplete conditions before encoding', () => {
    const model = group(
      { id: 'a', attributeKind: null, key: '', operator: 'eq', value: '' },
      { id: 'b', attributeKind: 'resource', key: 'service.name', operator: 'eq', value: 'x' }
    )

    expect(toAttributeFilter(model)).toEqual({
      type: 'equals',
      key: { kind: 'resource', name: 'service.name' },
      value: 'x'
    })
  })

  test('encodes an empty model as an empty AND (match everything)', () => {
    expect(toAttributeFilter([])).toEqual({ type: 'and', conjuncts: [] })
  })
})

describe('fromAttributeFilter', () => {
  test('decodes an OR of ANDs into groups, including exists', () => {
    const filter: AttributeFilter = {
      type: 'or',
      disjuncts: [
        {
          type: 'and',
          conjuncts: [
            { type: 'equals', key: { kind: 'resource', name: 'k1' }, value: 'v1' },
            { type: 'exists', key: { kind: 'scope', name: 'k2' } }
          ]
        },
        { type: 'equals', key: { kind: 'resource', name: 'k3' }, value: 'v3' }
      ]
    }

    expect(
      fromAttributeFilter(filter, newId).map((g) =>
        g.conditions.map((c) => [c.attributeKind, c.key, c.operator])
      )
    ).toEqual([
      [
        ['resource', 'k1', 'eq'],
        ['scope', 'k2', 'exists']
      ],
      [['resource', 'k3', 'eq']]
    ])
  })

  test.each<[AttributeFilter, [AttributeKind, string, Operator, string]]>([
    [
      { type: 'exists', key: { kind: 'resource', name: 'service.name' } },
      ['resource', 'service.name', 'not_exists', '']
    ],
    [
      { type: 'equals', key: { kind: 'resource', name: 'service.name' }, value: 'v' },
      ['resource', 'service.name', 'neq', 'v']
    ],
    [
      { type: 'contains', key: { kind: 'resource', name: 'service.name' }, value: 'v' },
      ['resource', 'service.name', 'not_contains', 'v']
    ],
    [
      { type: 'starts_with', key: { kind: 'resource', name: 'service.name' }, value: 'v' },
      ['resource', 'service.name', 'not_starts_with', 'v']
    ],
    [
      { type: 'ends_with', key: { kind: 'resource', name: 'service.name' }, value: 'v' },
      ['resource', 'service.name', 'not_ends_with', 'v']
    ],
    [
      { type: 'regex', key: { kind: 'resource', name: 'service.name' }, value: 'v.*' },
      ['resource', 'service.name', 'not_regex', 'v.*']
    ]
  ])('decodes a not(...) node into the matching negated operator', (condition, expected) => {
    const filter: AttributeFilter = { type: 'not', condition }

    expect(
      fromAttributeFilter(filter, newId).flatMap((g) =>
        g.conditions.map((c) => [c.attributeKind, c.key, c.operator, c.value])
      )
    ).toEqual([expected])
  })

  test('round-trips a model through toAttributeFilter -> fromAttributeFilter', () => {
    const model = modelFromLists(lists)
    const shape = (m: AttributeFilterModel) =>
      m.map((g) => g.conditions.map((c) => [c.attributeKind, c.key, c.value, c.operator]))
    expect(shape(fromAttributeFilter(toAttributeFilter(model), newId))).toEqual(shape(model))
  })

  test('throws on a filter that is not in disjunctive normal form', () => {
    const filter: AttributeFilter = {
      type: 'and',
      conjuncts: [{ type: 'or', disjuncts: [] }]
    }

    expect(() => fromAttributeFilter(filter, newId)).toThrow(/disjunctive normal form/)
  })
})
