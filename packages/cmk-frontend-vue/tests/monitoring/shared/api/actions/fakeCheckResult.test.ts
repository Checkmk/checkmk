/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { FakeCheckResultApi } from '@/monitoring/shared/api/actions/fakeCheckResult'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }
const OPTIONS = { state: 1, pluginOutput: 'Testing', metrics: 'rta=0.5ms' }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { faked: 2 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('posts the hosts with the result and returns the faked count', async () => {
  const hosts = [
    { site_id: 'local', name: 'db-1' },
    { site_id: 'remote', name: 'web-1' }
  ]

  expect(await new FakeCheckResultApi().fakeHosts(hosts, OPTIONS)).toBe(2)
  expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/fake_check_result', {
    ...CONTENT_TYPE,
    body: { hosts, state: 1, plugin_output: 'Testing', metrics: 'rta=0.5ms' }
  })
})

test('posts the services of the host with the result', async () => {
  await new FakeCheckResultApi().fakeServices(
    [{ host: { site_id: 'local', name: 'db-1' }, description: 'CPU load' }],
    {
      ...OPTIONS,
      state: 2
    }
  )

  expect(postSpy).toHaveBeenCalledWith('/monitor/services/actions/fake_check_result', {
    ...CONTENT_TYPE,
    body: {
      services: [{ site_id: 'local', host_name: 'db-1', name: 'CPU load' }],
      state: 2,
      plugin_output: 'Testing',
      metrics: 'rta=0.5ms'
    }
  })
})
