/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { defineComponent, nextTick, ref } from 'vue'

import type { ConsolidationFn, HorizontalLine, Metric } from '@/graphing/components/TimeSeriesGraph'
import { useGraphVisibility } from '@/graphing/composables/useGraphVisibility'

// Minimal fixtures — the composable only accesses metadata.name and line.name
const CPU = { metadata: { name: 'cpu' } } as Metric
const MEM = { metadata: { name: 'mem' } } as Metric
const WARNING_LINE = { name: 'Warning' } as HorizontalLine

function mountComposable(
  initialMetrics: Metric[] = [],
  initialLines: HorizontalLine[] = [],
  initialConsolidationFunction: ConsolidationFn | undefined = undefined
) {
  const metricsRef = ref(initialMetrics)
  const linesRef = ref(initialLines)
  const consolidationFunctionRef = ref<ConsolidationFn | undefined>(initialConsolidationFunction)
  let api!: ReturnType<typeof useGraphVisibility>
  render(
    defineComponent({
      setup() {
        api = useGraphVisibility(
          () => metricsRef.value,
          () => linesRef.value,
          () => consolidationFunctionRef.value
        )
        return () => null
      }
    })
  )
  return { api, metricsRef, linesRef, consolidationFunctionRef }
}

test('visibleMetrics initially contains all metrics', () => {
  const { api } = mountComposable([CPU, MEM])
  expect(api.visibleMetrics.value).toHaveLength(2)
})

test('visibleMetrics excludes metrics listed in hiddenMetricNames', () => {
  const { api } = mountComposable([CPU, MEM])
  api.hiddenMetricNames.value = ['cpu']
  expect(api.visibleMetrics.value.map((m) => m.metadata.name)).toEqual(['mem'])
})

test('visibleHorizontalLines initially contains all lines', () => {
  const { api } = mountComposable([], [WARNING_LINE])
  expect(api.visibleHorizontalLines.value).toHaveLength(1)
})

test('visibleHorizontalLines excludes lines listed in hiddenLineNames', () => {
  const { api } = mountComposable([], [WARNING_LINE])
  api.hiddenLineNames.value = ['Warning']
  expect(api.visibleHorizontalLines.value).toHaveLength(0)
})

test('activeConsolidationFunction initializes from the getConsolidationFunction getter', () => {
  const { api } = mountComposable([], [], 'min')
  expect(api.activeConsolidationFunction.value).toBe('min')
})

test('activeConsolidationFunction defaults to max when getConsolidationFunction returns undefined', () => {
  const { api } = mountComposable([], [], undefined)
  expect(api.activeConsolidationFunction.value).toBe('max')
})

test('setConsolidationFunction updates activeConsolidationFunction', () => {
  const { api } = mountComposable([], [], 'min')
  api.setConsolidationFunction('avg')
  expect(api.activeConsolidationFunction.value).toBe('avg')
})

test('activeConsolidationFunction tracks the getConsolidationFunction getter reactively when the source changes', async () => {
  const { api, consolidationFunctionRef } = mountComposable([], [], 'min')
  consolidationFunctionRef.value = 'max'
  await nextTick()
  expect(api.activeConsolidationFunction.value).toBe('max')
})

test('highlightedMetricName starts as null', () => {
  const { api } = mountComposable([CPU])
  expect(api.highlightedMetricName.value).toBeNull()
})
