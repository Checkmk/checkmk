/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import { toTimeSeriesGraph } from '@/graphing/api/discoveredGraph'

test('a discovered graph is dressed as the graph the renderer takes, at the size and interaction given', () => {
  const size = { width: 330, height: 110, mode: 'fixed' } as const
  const interaction = {
    burger: 'disabled',
    zoom: 'disabled',
    panning: 'disabled',
    hover: 'disabled',
    brush: 'disabled',
    pin: 'disabled'
  } as const

  const graph = toTimeSeriesGraph(
    {
      internal: '{"graphs":[]}',
      title: 'CPU utilization',
      name: 'cpu_utilization',
      add_to_specification: null,
      add_type: null,
      y_axis: null
    },
    size,
    interaction
  )

  expect(graph.internal).toBe('{"graphs":[]}')
  expect(graph.options.name).toBe('cpu_utilization')
  expect(graph.options.header).toEqual({ title: 'CPU utilization', show_graph_time: true })
  expect(graph.size).toEqual(size)
  expect(graph.interaction).toEqual(interaction)
})
