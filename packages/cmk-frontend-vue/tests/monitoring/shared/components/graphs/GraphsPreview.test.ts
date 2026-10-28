/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, expect, test, vi } from 'vitest'

import type { HostRef } from '@/monitoring/shared/api/types'
import GraphsPreview from '@/monitoring/shared/components/graphs/GraphsPreview.vue'

const HOST: HostRef = { site_id: 'local', name: 'web-server-01' }

function discoverAnswers(status: number, body: object): void {
  vi.spyOn(client, 'POST').mockResolvedValue(
    (status < 400
      ? { data: body, response: new Response(null, { status }) }
      : { data: undefined, error: body, response: new Response(null, { status }) }) as never
  )
}

function mountPreview() {
  return render(GraphsPreview, { props: { host: HOST, service: 'CPU load' } })
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('asks the host the service runs on for the graphs of that service', () => {
  discoverAnswers(200, { graphs: [], no_data_message: null })

  mountPreview()

  expect(client.POST).toHaveBeenCalledWith(
    '/domain-types/graph/actions/discover_template_graphs/invoke',
    expect.objectContaining({
      body: {
        hostname: 'web-server-01',
        service_description: 'CPU load',
        site: 'local',
        graph_id: null
      }
    })
  )
})

test('a service Checkmk has no graphs for is explained rather than left blank', async () => {
  discoverAnswers(200, { graphs: [], no_data_message: null })

  mountPreview()

  expect(await screen.findByText('Checkmk has no graphs for this service.')).toBeInTheDocument()
})

test('a host Checkmk has no graphs for is explained as the host, not as a service', async () => {
  discoverAnswers(200, { graphs: [], no_data_message: null })

  render(GraphsPreview, { props: { host: HOST } })

  expect(await screen.findByText('Checkmk has no graphs for this host.')).toBeInTheDocument()
})

test("the backend's own explanation wins over the general one", async () => {
  discoverAnswers(200, { graphs: [], no_data_message: 'The host is not monitored.' })

  mountPreview()

  expect(await screen.findByText('The host is not monitored.')).toBeInTheDocument()
  expect(screen.queryByText('Checkmk has no graphs for this service.')).not.toBeInTheDocument()
})

test('a service whose graphs cannot be built shows why, as an error', async () => {
  discoverAnswers(422, {
    title: 'Graph cannot be built',
    detail: 'Cannot create graph with metrics of different units'
  })

  mountPreview()

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Cannot create graph with metrics of different units'
  )
})

test('graphs that fail to load say so, as an error', async () => {
  discoverAnswers(503, {
    title: 'Monitoring data source unavailable',
    detail: 'Connection refused'
  })

  mountPreview()

  expect(await screen.findByRole('alert')).toHaveTextContent('The graphs could not be loaded.')
})
