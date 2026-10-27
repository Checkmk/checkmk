/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { CustomNotificationApi } from '@/monitoring/shared/api/actions/customNotification'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }
const OPTIONS = { comment: 'Testing', forced: true, broadcast: false }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { notified: 2 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('posts the hosts with the options and returns the notified count', async () => {
  const hosts = [
    { site_id: 'local', name: 'db-1' },
    { site_id: 'remote', name: 'web-1' }
  ]

  expect(await new CustomNotificationApi().notifyHosts(hosts, OPTIONS)).toBe(2)
  expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/custom_notification', {
    ...CONTENT_TYPE,
    body: { hosts, ...OPTIONS }
  })
})

test('posts the services of the host with the options', async () => {
  const host = { site_id: 'local', name: 'db-1' }
  await new CustomNotificationApi().notifyServices(
    [
      { host, description: 'CPU load' },
      { host, description: 'Memory' }
    ],
    OPTIONS
  )

  expect(postSpy).toHaveBeenCalledWith('/monitor/services/actions/custom_notification', {
    ...CONTENT_TYPE,
    body: {
      services: [
        { site_id: 'local', host_name: 'db-1', name: 'CPU load' },
        { site_id: 'local', host_name: 'db-1', name: 'Memory' }
      ],
      ...OPTIONS
    }
  })
})
