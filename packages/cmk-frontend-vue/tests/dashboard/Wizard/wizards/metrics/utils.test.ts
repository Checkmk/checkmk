/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { Graph } from '@/dashboard/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'
import { getGraph, getMetricFromWidget } from '@/dashboard/components/Wizard/wizards/metrics/utils'
import type { WidgetSpec } from '@/dashboard/types/widget'

function mockWidget(content: object): WidgetSpec {
  return { content } as WidgetSpec
}

describe('getMetricFromWidget', () => {
  it('should return null for null widget', () => {
    expect(getMetricFromWidget(null)).toBeNull()
  })

  it('should return null for undefined widget', () => {
    expect(getMetricFromWidget(undefined)).toBeNull()
  })

  it('should return metric field when present', () => {
    expect(getMetricFromWidget(mockWidget({ metric: 'cpu_load' }))).toBe('cpu_load')
  })

  it('should return source field when present and no metric', () => {
    expect(getMetricFromWidget(mockWidget({ source: 'mem_used' }))).toBe('mem_used')
  })

  it('should return graph_template field when present and no metric or source', () => {
    expect(getMetricFromWidget(mockWidget({ graph_template: 'cpu_utilization' }))).toBe(
      'cpu_utilization'
    )
  })

  it('should prioritize metric over source and graph_template', () => {
    expect(
      getMetricFromWidget(
        mockWidget({ metric: 'cpu_load', source: 'mem_used', graph_template: 'tpl' })
      )
    ).toBe('cpu_load')
  })

  it('should return null when content has none of the expected fields', () => {
    expect(getMetricFromWidget(mockWidget({ type: 'some_other' }))).toBeNull()
  })
})

describe('getGraph', () => {
  const enabledWidgets = [Graph.SINGLE_GRAPH, Graph.GAUGE, Graph.BARPLOT]

  it('should return first enabled widget when widget arg is falsy', () => {
    expect(getGraph(enabledWidgets)).toBe(Graph.SINGLE_GRAPH)
    expect(getGraph(enabledWidgets, '')).toBe(Graph.SINGLE_GRAPH)
    expect(getGraph(enabledWidgets, undefined)).toBe(Graph.SINGLE_GRAPH)
  })

  it('should return matching Graph enum value when enabled', () => {
    expect(getGraph(enabledWidgets, Graph.GAUGE)).toBe(Graph.GAUGE)
  })

  it('should fall back to first enabled widget when match is not enabled', () => {
    expect(getGraph(enabledWidgets, Graph.SCATTERPLOT)).toBe(Graph.SINGLE_GRAPH)
  })

  it('should fall back to first enabled widget when no match in Graph enum', () => {
    expect(getGraph(enabledWidgets, 'nonexistent_graph')).toBe(Graph.SINGLE_GRAPH)
  })

  it('should return null when enabled list is empty', () => {
    expect(getGraph([], Graph.SINGLE_GRAPH)).toBeNull()
  })

  it('should return null when enabled list is empty and widget is falsy', () => {
    expect(getGraph([])).toBeNull()
  })
})
