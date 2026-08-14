/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Metric } from '@/graphing/components/TimeSeriesGraph'
import {
  type MetricAttribute,
  attributesOf,
  groupedAttributes,
  hasAttributes,
  sortedAttributes
} from '@/graphing/components/metricAttributes'

const UNIT: Metric['metadata']['unit'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

function metricWith(attributes?: MetricAttribute[]): Metric {
  return {
    metadata: {
      name: 'm',
      title: 'M',
      unit: UNIT,
      color: '#ff0000',
      ...(attributes === undefined ? {} : { attributes })
    },
    render: { stack: null, inverse: false, hidden: false },
    data_points: [1]
  }
}

const HOST_ARCH: MetricAttribute = { kind: 'resource', name: 'host.arch', value: 'x64' }
const SCOPE_NAME: MetricAttribute = { kind: 'scope', name: 'scope.name', value: 'otel' }
const STATUS: MetricAttribute = { kind: 'data_point', name: 'status', value: '304' }

test('a metric fetched from an RRD carries no attributes', () => {
  expect(attributesOf(metricWith())).toEqual([])
  expect(hasAttributes(metricWith())).toBe(false)
  expect(hasAttributes(metricWith([]))).toBe(false)
})

test('the flat listing puts resource before scope before data point', () => {
  const sorted = sortedAttributes([STATUS, SCOPE_NAME, HOST_ARCH])
  expect(sorted.map((attribute) => attribute.kind)).toEqual(['resource', 'scope', 'data_point'])
})

test('the flat listing keeps the response order within a kind', () => {
  const first: MetricAttribute = { kind: 'resource', name: 'host.arch', value: 'x64' }
  const second: MetricAttribute = { kind: 'resource', name: 'host.name', value: 'collector' }

  const sorted = sortedAttributes([first, second])

  expect(sorted).toEqual([first, second])
})

test('a kind we do not know sorts after the ones we do', () => {
  const unknown: MetricAttribute = { kind: 'galaxy', name: 'g', value: '1' }

  const sorted = sortedAttributes([unknown, STATUS, HOST_ARCH])

  expect(sorted.map((attribute) => attribute.kind)).toEqual(['resource', 'data_point', 'galaxy'])
})

test('grouping skips the kinds there are no attributes of', () => {
  const groups = groupedAttributes([STATUS, HOST_ARCH])

  expect(groups).toEqual([
    { kind: 'resource', attributes: [HOST_ARCH] },
    { kind: 'data_point', attributes: [STATUS] }
  ])
})

test('grouping keeps a kind we do not know as its own group', () => {
  const unknown: MetricAttribute = { kind: 'galaxy', name: 'g', value: '1' }

  const groups = groupedAttributes([unknown, HOST_ARCH])

  expect(groups).toEqual([
    { kind: 'resource', attributes: [HOST_ARCH] },
    { kind: 'galaxy', attributes: [unknown] }
  ])
})
