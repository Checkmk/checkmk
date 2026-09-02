/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import type { DiscoveredGraph } from '@/monitoring/host-services/api/graphs'
import ServiceGraphsTab, {
  type ServiceGraphs,
  toTimeSeriesGraph
} from '@/monitoring/host-services/components/slide-in/ServiceGraphsTab.vue'

const GRAPHS_LINK = 'view.py?view_name=service_graphs&site=local&host=web-1&service=CPU+load'

function makeShell(overrides: Partial<DiscoveredGraph> = {}): DiscoveredGraph {
  return {
    internal: '{"graphs":[]}',
    title: 'CPU utilization',
    name: 'cpu_utilization',
    add_to_specification: null,
    y_axis: null,
    ...overrides
  }
}

function mountTab(data: Partial<ServiceGraphs> = {}) {
  return render(ServiceGraphsTab, {
    props: {
      data: { graphs: [], noDataMessage: null, graphsLink: GRAPHS_LINK, ...data }
    }
  })
}

test('a service Checkmk has no graphs for is explained rather than left blank', () => {
  mountTab()

  expect(screen.getByText('Checkmk has no graphs for this service.')).toBeInTheDocument()
})

test("the backend's own explanation wins over the general one", () => {
  mountTab({ noDataMessage: 'The host is not monitored.' })

  expect(screen.getByText('The host is not monitored.')).toBeInTheDocument()
  expect(screen.queryByText('Checkmk has no graphs for this service.')).not.toBeInTheDocument()
})

test('the tab links to the graph page of the same host and service', () => {
  mountTab({ graphs: [makeShell()] })

  expect(screen.getByRole('link', { name: /Open the service graph page/ })).toHaveAttribute(
    'href',
    GRAPHS_LINK
  )
})

test('the link out leaves the frame the listing renders in, as every other one does', () => {
  mountTab({ graphs: [makeShell()] })

  expect(screen.getByRole('link', { name: /Open the service graph page/ })).toHaveAttribute(
    'target',
    '_top'
  )
})

test('a discovered shell is dressed as the graph the renderer takes', () => {
  const graph = toTimeSeriesGraph(makeShell(), 640)

  expect(graph.internal).toBe('{"graphs":[]}')
  expect(graph.options.name).toBe('cpu_utilization')
  expect(graph.options.header).toEqual({ title: 'CPU utilization', show_graph_time: true })
  expect(graph.size.width).toBe(640)
})

test('a graph in the panel cannot be pinned to the page it has none of', () => {
  expect(toTimeSeriesGraph(makeShell(), 640).interaction.pin).toBe('disabled')
})
