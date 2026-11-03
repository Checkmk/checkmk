/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AllServicesApi } from '@/monitoring/all-services/api/services'

describe('AllServicesApi.fetchServices', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
    postSpy.mockResolvedValue({
      data: { services: [], meta: { limit: 1000, matched: 0, total: 0 } },
      error: undefined,
      response: new Response()
    } as never)
  })

  it('lists the services of every host, naming neither a host nor a site', async () => {
    await new AllServicesApi().fetchServices({ limit: 50 })

    expect(postSpy).toHaveBeenCalledWith('/monitor/services', {
      params: { header: { 'Content-Type': 'application/json' } },
      body: { limit: 50 }
    })
  })

  it('sends the host name and site conditions of the filter', async () => {
    await new AllServicesApi().fetchServices({
      filter: {
        type: 'and',
        children: [
          { type: 'condition', field: 'host_name', op: 'contains', value: 'web' },
          { type: 'condition', field: 'site_id', op: 'one_of', value: ['remote'] }
        ]
      }
    })

    expect(postSpy.mock.calls[0][1].body.filter).toEqual({
      type: 'and',
      children: [
        { type: 'condition', field: 'host_name', op: 'contains', value: 'web' },
        { type: 'condition', field: 'site_id', op: 'one_of', value: ['remote'] }
      ]
    })
  })
})
