/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { ModifiedAttributesApi } from '@/monitoring/shared/api/actions/modifiedAttributes'

const CONTENT_TYPE = { params: { header: { 'Content-Type': 'application/json' } } }
const HOSTS = [
  { site_id: 'local', name: 'db-1' },
  { site_id: 'remote', name: 'web-1' }
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { modified: 2 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('posts the hosts with the attribute to switch and returns the modified count', async () => {
  expect(await new ModifiedAttributesApi().toggleHosts(HOSTS, 'notifications', false)).toBe(2)
  expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/toggle_attribute', {
    ...CONTENT_TYPE,
    body: { hosts: HOSTS, attribute: 'notifications', enabled: false }
  })
})

test('posts the hosts to reset', async () => {
  await new ModifiedAttributesApi().resetHosts(HOSTS)

  expect(postSpy).toHaveBeenCalledWith('/monitor/hosts/actions/reset_modified_attributes', {
    ...CONTENT_TYPE,
    body: { hosts: HOSTS }
  })
})
