/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { expect, test, vi } from 'vitest'

import { GraphsApi } from '@/monitoring/shared/api/graphs'

const HOST = { site_id: 'local', name: 'localhost' }

const UNIT_MISMATCH =
  "Cannot create graph with metrics of different units: Unit(notation=IECNotation(symbol='B'))"

function respondWith(status: number, body: object): void {
  vi.spyOn(client, 'POST').mockResolvedValue({
    data: undefined,
    error: body,
    response: new Response(null, { status })
  } as never)
}

test('a service whose graphs cannot be built is answered with the reason the backend gives', async () => {
  respondWith(422, { title: 'Graph cannot be built', detail: UNIT_MISMATCH })

  expect(await new GraphsApi().discover(HOST, 'Memory')).toEqual({
    graphs: [],
    noDataMessage: null,
    errorMessage: UNIT_MISMATCH
  })
})

test.each([
  {
    outcome: 'a monitoring core that does not answer stays a failure, for the reader to retry',
    status: 503,
    problem: { title: 'Monitoring data source unavailable', detail: 'Connection refused' }
  },
  {
    outcome: 'a crash of the endpoint stays a failure, for the reader to retry and report',
    status: 500,
    problem: { title: 'Graph discovery failed', detail: "Failed to discover graphs: 'unit'" }
  },
  {
    outcome: 'a 422 for another reason stays a failure, for the reader to retry',
    status: 422,
    problem: { title: 'Unprocessable Content', detail: 'Body is not valid' }
  }
])('$outcome', async ({ status, problem }) => {
  respondWith(status, problem)

  await expect(new GraphsApi().discover(HOST, 'Memory')).rejects.toThrow(problem.detail)
})

test('discovered graphs carry no error', async () => {
  vi.spyOn(client, 'POST').mockResolvedValue({
    data: { graphs: [], no_data_message: 'No data' },
    response: new Response(null, { status: 200 })
  } as never)

  expect(await new GraphsApi().discover(HOST, 'Memory')).toEqual({
    graphs: [],
    noDataMessage: 'No data',
    errorMessage: null
  })
})

test('the graphs of the host itself are asked for under the name the backend reads as the host', async () => {
  vi.spyOn(client, 'POST').mockResolvedValue({
    data: { graphs: [], no_data_message: null },
    response: new Response(null, { status: 200 })
  } as never)

  await new GraphsApi().discover(HOST)

  expect(client.POST).toHaveBeenCalledWith(
    '/domain-types/graph/actions/discover_template_graphs/invoke',
    expect.objectContaining({
      body: { hostname: 'localhost', service_description: '_HOST_', site: 'local', graph_id: null }
    })
  )
})
