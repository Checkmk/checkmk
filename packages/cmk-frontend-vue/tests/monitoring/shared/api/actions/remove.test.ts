/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { AcknowledgeApi } from '@/monitoring/shared/api/actions/acknowledge'
import { DowntimeApi } from '@/monitoring/shared/api/actions/downtime'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }

// A host name two sites monitor: each row must keep its own site.
const HOSTS = [
  { site_id: 'local', name: 'web-1' },
  { site_id: 'remote', name: 'web-1' }
]
const SERVICES = HOSTS.map((host) => ({ host, description: 'CPU load' }))
const SERVICE_TARGETS = [
  { site_id: 'local', host_name: 'web-1', name: 'CPU load' },
  { site_id: 'remote', host_name: 'web-1', name: 'CPU load' }
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { removed: 2 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('removes the acknowledgements of the hosts, each on its site', async () => {
  expect(await new AcknowledgeApi().removeHostAcknowledgements(HOSTS)).toBe(2)

  expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/remove_acknowledgements', {
    ...CONTENT_TYPE,
    body: { hosts: HOSTS }
  })
})

test('removes the acknowledgements of the services, each on the site of its host', async () => {
  expect(await new AcknowledgeApi().removeServiceAcknowledgements(SERVICES)).toBe(2)

  expect(postSpy).toHaveBeenCalledWith('/monitor/services/actions/remove_acknowledgements', {
    ...CONTENT_TYPE,
    body: { services: SERVICE_TARGETS }
  })
})

test('removes the downtimes of the hosts, each on its site', async () => {
  expect(await new DowntimeApi().removeHostDowntimes(HOSTS)).toBe(2)

  expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/remove_downtimes', {
    ...CONTENT_TYPE,
    body: { hosts: HOSTS }
  })
})

test('removes the downtimes of the services, each on the site of its host', async () => {
  expect(await new DowntimeApi().removeServiceDowntimes(SERVICES)).toBe(2)

  expect(postSpy).toHaveBeenCalledWith('/monitor/services/actions/remove_downtimes', {
    ...CONTENT_TYPE,
    body: { services: SERVICE_TARGETS }
  })
})
