/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Metric, MetricRender } from '@/graphing/components/TimeSeriesGraph'
import { orderMetricsTopToBottom } from '@/graphing/components/metricOrder'

function metric(name: string, render: MetricRender): Metric {
  return {
    metadata: {
      name,
      title: name,
      unit: {
        notation: 'decimal',
        symbol: '',
        precision: { type: 'auto', digits: 2 },
        convertible: true
      },
      color: '#ff0000',
      attributes: []
    },
    render,
    data_points: [1]
  }
}

const FLAGS = { inverse: false, hidden: false }
const MIRRORED = { inverse: true, hidden: false }

function names(metrics: Metric[]): string[] {
  return metrics.map((entry) => entry.metadata.name)
}

describe('orderMetricsTopToBottom', () => {
  it('lists bars below the lines and areas that overlay them', () => {
    const ordered = orderMetricsTopToBottom([
      metric('bar', { shape: 'bar', stack: null, aggregation: 'sum', ...FLAGS }),
      metric('area', { shape: 'area', stack: 's', ...FLAGS }),
      metric('line', { shape: 'line', ...FLAGS })
    ])

    expect(names(ordered)).toEqual(['line', 'area', 'bar'])
  })

  it('lists a bar stack topmost layer first', () => {
    const ordered = orderMetricsTopToBottom([
      metric('bottom', { shape: 'bar', stack: 's', aggregation: 'sum', ...FLAGS }),
      metric('top', { shape: 'bar', stack: 's', aggregation: 'sum', ...FLAGS })
    ])

    expect(names(ordered)).toEqual(['top', 'bottom'])
  })

  it('lists mirrored bars right below the baseline, above mirrored areas and lines', () => {
    const ordered = orderMetricsTopToBottom([
      metric('line', { shape: 'line', ...MIRRORED }),
      metric('area', { shape: 'area', stack: 's', ...MIRRORED }),
      metric('bar', { shape: 'bar', stack: null, aggregation: 'sum', ...MIRRORED })
    ])

    expect(names(ordered)).toEqual(['bar', 'area', 'line'])
  })
})
