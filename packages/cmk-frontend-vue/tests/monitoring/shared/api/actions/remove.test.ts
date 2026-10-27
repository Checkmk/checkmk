/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { AcknowledgeApi } from '@/monitoring/shared/api/actions/acknowledge'
import { RemoveDowntimeApi } from '@/monitoring/shared/api/actions/downtime'

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

test('removes only the downtimes of the hosts themselves', async () => {
  await new RemoveDowntimeApi().removeHostDowntimes(['db-1'])

  expect(postSpy).toHaveBeenCalledWith('/domain-types/downtime/actions/delete/invoke', {
    ...CONTENT_TYPE,
    body: {
      delete_type: 'query',
      query: {
        op: 'and',
        expr: [
          { op: '=', left: 'is_service', right: '0' },
          { op: 'or', expr: [{ op: '=', left: 'host_name', right: 'db-1' }] }
        ]
      }
    }
  })
})

test('removes the downtimes of the services, matched by host and service', async () => {
  await new RemoveDowntimeApi().removeServiceDowntimes([
    { host: { name: 'db-1', site_id: 'local' }, description: 'CPU load' },
    { host: { name: 'web-1', site_id: 'remote' }, description: 'Memory' }
  ])

  expect(postSpy).toHaveBeenCalledWith('/domain-types/downtime/actions/delete/invoke', {
    ...CONTENT_TYPE,
    body: {
      delete_type: 'query',
      query: {
        op: 'or',
        expr: [
          {
            op: 'and',
            expr: [
              { op: '=', left: 'host_name', right: 'db-1' },
              { op: 'or', expr: [{ op: '=', left: 'service_description', right: 'CPU load' }] }
            ]
          },
          {
            op: 'and',
            expr: [
              { op: '=', left: 'host_name', right: 'web-1' },
              { op: 'or', expr: [{ op: '=', left: 'service_description', right: 'Memory' }] }
            ]
          }
        ]
      }
    }
  })
})
