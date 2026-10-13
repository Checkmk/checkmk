/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { defineComponent } from 'vue'

import type { Formula } from '@/graphing/designer/calculation/formula'
import { useItemDescription } from '@/graphing/designer/composables/useItemDescription'

import {
  constantItem,
  formulaItem,
  rrdMetricItem,
  rrdQueryItem,
  scalarItem,
  telemetryMetricsItem
} from '../fixtures'

function mountDescriptions(): ReturnType<typeof useItemDescription> {
  let api!: ReturnType<typeof useItemDescription>
  render(
    defineComponent({
      setup() {
        api = useItemDescription()
        return () => null
      }
    })
  )
  return api
}

test('describes an RRD metric as host > service > metric', () => {
  const { describeItem } = mountDescriptions()
  expect(describeItem(rrdMetricItem('A'))).toBe('my-host > CPU utilization > util')
})

test('describes a scalar with its friendly scalar name', () => {
  const { describeItem } = mountDescriptions()
  expect(describeItem(scalarItem('A'))).toBe('my-host > CPU utilization > util > Warning')
  expect(describeItem(scalarItem('A', { scalar_type: 'critical_lower' }))).toBe(
    'my-host > CPU utilization > util > Critical lower'
  )
})

test('describes an RRD query with generic filter terms', () => {
  const { describeItem } = mountDescriptions()
  expect(describeItem(rrdQueryItem('C'))).toBe('Host filter > Service filter > util')
})

test('describes a constant with its value', () => {
  const { describeItem } = mountDescriptions()
  expect(describeItem(constantItem('K', { value: 42 }))).toBe('Constant 42')
})

test('describes an OpenTelemetry metrics query by its metric name', () => {
  const { describeItem } = mountDescriptions()
  expect(describeItem(telemetryMetricsItem('E'))).toBe('span.latency')
})

test('describes a formula as its expression, never its title', () => {
  const { describeItem } = mountDescriptions()
  const ast: Formula = {
    op: 'difference',
    operands: [
      { op: 'ref', id: 'A' },
      { op: 'ref', id: 'B' }
    ]
  }
  expect(describeItem(formulaItem('D', { ast, title: 'My custom title' }))).toBe('= A - B')
})

test('describes a percentile with a localized ordinal, stopping at the ref', () => {
  const { describeItem } = mountDescriptions()
  const p95: Formula = { op: 'percentile', percentile: 95, operand: { op: 'ref', id: 'B' } }
  expect(describeItem(formulaItem('D', { ast: p95 }))).toBe('95th percentile of B')

  const p1: Formula = { op: 'percentile', percentile: 1, operand: { op: 'ref', id: 'B' } }
  expect(describeItem(formulaItem('E', { ast: p1 }))).toBe('1st percentile of B')
})
