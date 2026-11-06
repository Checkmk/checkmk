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
    data: { commented: 2 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('comments the hosts, each on its site', async () => {
  const hosts = [
    { site_id: 'local', name: 'web-1' },
    { site_id: 'remote', name: 'web-1' }
  ]

  expect(await new CommentApi().commentHosts(hosts, 'Disk swap planned')).toBe(2)

  expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/add_comment', {
    ...CONTENT_TYPE,
    body: { hosts, comment: 'Disk swap planned' }
  })
})

test('comments the services, each on the site of its host', async () => {
  await new CommentApi().commentServices(
    [{ host: { name: 'web-1', site_id: 'remote' }, description: 'CPU load' }],
    'Known spike'
  )

  expect(postSpy).toHaveBeenCalledWith('/monitor/services/actions/add_comment', {
    ...CONTENT_TYPE,
    body: {
      services: [{ site_id: 'remote', host_name: 'web-1', name: 'CPU load' }],
      comment: 'Known spike'
    }
  })
})
