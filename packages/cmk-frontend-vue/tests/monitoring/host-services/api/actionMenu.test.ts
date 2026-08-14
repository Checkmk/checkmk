/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ServiceActionMenuApi } from '@/monitoring/host-services/api/actionMenu'
import type { HostRef, ServiceActionMenuItem } from '@/monitoring/shared/api/types'

const HOST: HostRef = { name: 'web-1', site_id: 'local' }

const ITEM: ServiceActionMenuItem = {
  icon_name: 'logwatch',
  title: 'Open log file viewer',
  url: 'view.py?view_name=logwatch&host=web-1&site=local'
}

describe('ServiceActionMenuApi.fetchActionMenu', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let getSpy: any

  beforeEach(() => {
    getSpy = vi.spyOn(client, 'GET')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockSuccess(items: ServiceActionMenuItem[]): void {
    getSpy.mockResolvedValueOnce({
      data: { items },
      error: undefined,
      response: new Response()
    } as never)
  }

  it('asks for the menu of one service of one host', async () => {
    mockSuccess([])

    await new ServiceActionMenuApi().fetchActionMenu(HOST, 'CPU load')

    expect(getSpy).toHaveBeenCalledWith('/monitor/hosts/{hostname}/service/action_menu', {
      params: {
        path: { hostname: 'web-1' },
        query: { site_id: 'local', service_name: 'CPU load' }
      }
    })
  })

  it('returns the entries the endpoint reports', async () => {
    mockSuccess([ITEM])

    expect(await new ServiceActionMenuApi().fetchActionMenu(HOST, 'CPU load')).toEqual([ITEM])
  })

  it('reports a failure to the caller rather than swallowing it', async () => {
    getSpy.mockResolvedValueOnce({
      data: undefined,
      error: { title: 'Not found', detail: 'no such service' },
      response: new Response(null, { status: 404 })
    } as never)

    await expect(new ServiceActionMenuApi().fetchActionMenu(HOST, 'CPU load')).rejects.toThrow()
  })
})
