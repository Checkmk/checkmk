/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { expect, test, vi } from 'vitest'

import { ServiceGraphsApi } from '@/monitoring/host-services/api/graphs'

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

  expect(await new ServiceGraphsApi().discover(HOST, 'Memory')).toEqual({
    graphs: [],
    noDataMessage: null,
    errorMessage: UNIT_MISMATCH
  })
})

test('a monitoring core that does not answer stays a failure, for the reader to retry', async () => {
  respondWith(503, { title: 'Monitoring data source unavailable', detail: 'Connection refused' })

  await expect(new ServiceGraphsApi().discover(HOST, 'Memory')).rejects.toThrow(
    'Connection refused'
  )
})

test('a crash of the endpoint stays a failure, for the reader to retry and report', async () => {
  respondWith(500, {
    title: 'Graph discovery failed',
    detail: "Failed to discover graphs: 'unit'"
  })

  await expect(new ServiceGraphsApi().discover(HOST, 'Memory')).rejects.toThrow(
    "Failed to discover graphs: 'unit'"
  )
})

test('discovered graphs carry no error', async () => {
  vi.spyOn(client, 'POST').mockResolvedValue({
    data: { graphs: [], no_data_message: 'No data' },
    response: new Response(null, { status: 200 })
  } as never)

  expect(await new ServiceGraphsApi().discover(HOST, 'Memory')).toEqual({
    graphs: [],
    noDataMessage: 'No data',
    errorMessage: null
  })
})
