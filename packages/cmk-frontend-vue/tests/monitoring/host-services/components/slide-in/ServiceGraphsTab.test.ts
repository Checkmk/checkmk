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
    add_type: null,
    y_axis: null,
    ...overrides
  }
}

function mountTab(data: Partial<ServiceGraphs> = {}) {
  return render(ServiceGraphsTab, {
    props: {
      data: {
        graphs: [],
        noDataMessage: null,
        errorMessage: null,
        graphsLink: GRAPHS_LINK,
        ...data
      }
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

test('a service whose graphs cannot be built shows why, as an error', () => {
  mountTab({ errorMessage: 'Cannot create graph with metrics of different units' })

  expect(screen.getByRole('alert')).toHaveTextContent(
    'Cannot create graph with metrics of different units'
  )
  expect(screen.queryByText('Checkmk has no graphs for this service.')).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Explore all service graphs/ })).toBeInTheDocument()
})

test('the tab links to the graph page of the same host and service', () => {
  mountTab({ graphs: [makeShell()] })

  expect(screen.getByRole('link', { name: /Explore all service graphs/ })).toHaveAttribute(
    'href',
    GRAPHS_LINK
  )
})

test('the link out leaves the frame the listing renders in, as every other one does', () => {
  mountTab({ graphs: [makeShell()] })

  expect(screen.getByRole('link', { name: /Explore all service graphs/ })).toHaveAttribute(
    'target',
    '_top'
  )
})

test('the graphs are headed by the time window they start with', () => {
  mountTab({ graphs: [makeShell()] })

  expect(
    screen.getByText(/Initially showing the last 8 days \(since \d{4}-\d{2}-\d{2} /)
  ).toBeInTheDocument()
})

test('a service without graphs names no time window', () => {
  mountTab()

  expect(screen.queryByText(/Initially showing the last/)).not.toBeInTheDocument()
})

test('a discovered shell is dressed as the graph the renderer takes', () => {
  const graph = toTimeSeriesGraph(makeShell(), 640)

  expect(graph.internal).toBe('{"graphs":[]}')
  expect(graph.options.name).toBe('cpu_utilization')
  expect(graph.options.header).toEqual({ title: 'CPU utilization', show_graph_time: true })
  expect(graph.size.width).toBe(640)
})

test('a graph in the panel can be pinned like on the graph page', () => {
  expect(toTimeSeriesGraph(makeShell(), 640).interaction.pin).toBe('enabled')
})
