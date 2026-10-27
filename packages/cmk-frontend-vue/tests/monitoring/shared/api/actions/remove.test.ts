/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { AcknowledgeApi } from '@/monitoring/shared/api/actions/acknowledge'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: undefined,
    error: undefined,
    response: new Response(null, { status: 204 })
  } as never)
})

test('removes the acknowledgements of the hosts by a query on their names', async () => {
  await new AcknowledgeApi().removeHostAcknowledgements(['db-1', 'web-1'])

  expect(postSpy).toHaveBeenCalledWith('/domain-types/acknowledge/actions/delete/invoke', {
    ...CONTENT_TYPE,
    body: {
      acknowledge_type: 'host_by_query',
      query: {
        op: 'or',
        expr: [
          { op: '=', left: 'name', right: 'db-1' },
          { op: '=', left: 'name', right: 'web-1' }
        ]
      }
    }
  })
})

test('removes the acknowledgements of the services of the host', async () => {
  await new AcknowledgeApi().removeServiceAcknowledgements([
    { host: { name: 'db-1', site_id: 'local' }, description: 'CPU load' }
  ])

  expect(postSpy).toHaveBeenCalledWith('/domain-types/acknowledge/actions/delete/invoke', {
    ...CONTENT_TYPE,
    body: {
      acknowledge_type: 'service_by_query',
      query: {
        op: 'and',
        expr: [
          { op: '=', left: 'host_name', right: 'db-1' },
          { op: 'or', expr: [{ op: '=', left: 'description', right: 'CPU load' }] }
        ]
      }
    }
  })
})
