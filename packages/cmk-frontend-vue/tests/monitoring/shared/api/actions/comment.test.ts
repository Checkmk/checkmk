/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { CommentApi } from '@/monitoring/shared/api/actions/comment'

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

test('comments the hosts by a query on their names, persistently', async () => {
  await new CommentApi().commentHosts(['db-1', 'web-1'], 'Disk swap planned')

  expect(postSpy).toHaveBeenCalledWith('/domain-types/comment/collections/host', {
    ...CONTENT_TYPE,
    body: {
      comment_type: 'host_by_query',
      query: {
        op: 'or',
        expr: [
          { op: '=', left: 'name', right: 'db-1' },
          { op: '=', left: 'name', right: 'web-1' }
        ]
      },
      comment: 'Disk swap planned',
      persistent: true
    }
  })
})

test('comments the services of the host by a query on their names, persistently', async () => {
  await new CommentApi().commentServices(
    [{ host: { name: 'db-1', site_id: 'local' }, description: 'CPU load' }],
    'Known spike'
  )

  expect(postSpy).toHaveBeenCalledWith('/domain-types/comment/collections/service', {
    ...CONTENT_TYPE,
    body: {
      comment_type: 'service_by_query',
      query: {
        op: 'and',
        expr: [
          { op: '=', left: 'host_name', right: 'db-1' },
          { op: 'or', expr: [{ op: '=', left: 'description', right: 'CPU load' }] }
        ]
      },
      comment: 'Known spike',
      persistent: true
    }
  })
})
