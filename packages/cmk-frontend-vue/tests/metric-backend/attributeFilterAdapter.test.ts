/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeFilterModel } from '@/metric-backend/attribute-filter/types'
import {
  type ThreeLists,
  buildAutocompleteContext,
  fromModel,
  toModel
} from '@/metric-backend/attributeFilterAdapter'

let counter = 0
function newId(): string {
  counter += 1
  return `id-${counter}`
}

const lists: ThreeLists = {
  resource: [{ key: 'service.name', value: 'frontend' }],
  scope: [{ key: 'otel.library.name', value: 'http' }],
  datapoint: [
    { key: 'http.method', value: 'GET' },
    { key: 'http.route', value: '/api' }
  ]
}

describe('toModel', () => {
  test('concatenates resource -> scope -> datapoint into one AND chain', () => {
    const model = toModel(lists, newId)

    expect(model.map((c) => [c.attributeType, c.key, c.value, c.connector])).toEqual([
      ['resource', 'service.name', 'frontend', null],
      ['scope', 'otel.library.name', 'http', 'AND'],
      ['datapoint', 'http.method', 'GET', 'AND'],
      ['datapoint', 'http.route', '/api', 'AND']
    ])
    expect(model.every((c) => c.operator === 'eq')).toBe(true)
  })

  test('produces an empty model for empty lists', () => {
    expect(toModel({ resource: [], scope: [], datapoint: [] }, newId)).toEqual([])
  })
})

describe('fromModel', () => {
  test('buckets conditions back into the three lists by attributeType', () => {
    const model = toModel(lists, newId)
    expect(fromModel(model)).toEqual(lists)
  })

  test('drops conditions with no attributeType or empty key (pills still being created)', () => {
    const model: AttributeFilterModel = [
      { id: 'a', attributeType: null, key: '', operator: 'eq', value: '', connector: null },
      { id: 'b', attributeType: 'resource', key: '', operator: 'eq', value: 'x', connector: 'AND' },
      {
        id: 'c',
        attributeType: 'scope',
        key: 'otel.library.name',
        operator: 'eq',
        value: 'http',
        connector: 'AND'
      }
    ]

    expect(fromModel(model)).toEqual({
      resource: [],
      scope: [{ key: 'otel.library.name', value: 'http' }],
      datapoint: []
    })
  })

  test('round-trips a model through fromModel -> toModel preserving content', () => {
    const model = toModel(lists, newId)
    expect(fromModel(toModel(fromModel(model), newId))).toEqual(lists)
  })
})

describe('buildAutocompleteContext', () => {
  test('emits per-type cascading attrs plus metric name and static keys', () => {
    const model = toModel(lists, newId)
    const context = buildAutocompleteContext(model, {
      metricName: 'http_requests',
      staticResourceAttributeKeys: ['service.name']
    })

    expect(context).toEqual({
      metric_name: 'http_requests',
      resource_attributes: [{ key: 'service.name', value: 'frontend' }],
      scope_attributes: [{ key: 'otel.library.name', value: 'http' }],
      data_point_attributes: [
        { key: 'http.method', value: 'GET' },
        { key: 'http.route', value: '/api' }
      ],
      static_resource_attribute_keys: ['service.name']
    })
  })

  test('omits incomplete conditions (missing key or value) from the context', () => {
    const model: AttributeFilterModel = [
      {
        id: 'a',
        attributeType: 'resource',
        key: 'service.name',
        operator: 'eq',
        value: '',
        connector: null
      },
      {
        id: 'b',
        attributeType: 'resource',
        key: 'host.name',
        operator: 'eq',
        value: 'web-01',
        connector: 'AND'
      }
    ]

    expect(buildAutocompleteContext(model)).toEqual({
      resource_attributes: [{ key: 'host.name', value: 'web-01' }]
    })
  })

  test('excludes the condition being edited via excludeId', () => {
    const model: AttributeFilterModel = [
      {
        id: 'self',
        attributeType: 'datapoint',
        key: 'http.method',
        operator: 'eq',
        value: 'GET',
        connector: null
      },
      {
        id: 'other',
        attributeType: 'datapoint',
        key: 'http.route',
        operator: 'eq',
        value: '/api',
        connector: 'AND'
      }
    ]

    const context = buildAutocompleteContext(model, {
      attributeKey: 'http.method',
      excludeId: 'self'
    })

    expect(context).toEqual({
      data_point_attributes: [{ key: 'http.route', value: '/api' }],
      attribute_key: 'http.method'
    })
  })

  test('omits empty optional fields', () => {
    expect(buildAutocompleteContext([])).toEqual({})
  })
})
