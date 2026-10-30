/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { HostActionMenuApi } from '@/monitoring/shared/api/hostActionMenu'
import type { ActionMenuItem } from '@/monitoring/shared/api/types'

const ITEM: ActionMenuItem = {
  icon_name: 'status',
  title: 'Open host status',
  url: 'view.py?view_name=host&host=web-1&site=local'
}

// Only the site that monitors web-1 knows its menu.
useMswServer(
  restApiHttp.get('/monitor/hosts/{hostname}/action_menu', ({ params, query, response }) => {
    if (params.hostname === 'web-1' && query.get('site_id') === 'local') {
      return response(200).json({ items: [ITEM] })
    }
    return response.untyped(
      HttpResponse.json({ title: 'Not found', detail: 'no such host' }, { status: 404 })
    )
  })
)

describe('HostActionMenuApi.fetchActionMenu', () => {
  it('asks for the menu of one host on the site that monitors it', async () => {
    const items = await new HostActionMenuApi().fetchActionMenu({ name: 'web-1', site_id: 'local' })

    expect(items).toEqual([ITEM])
  })

  it('reports a failure to the caller rather than swallowing it', async () => {
    const request = new HostActionMenuApi().fetchActionMenu({ name: 'web-1', site_id: 'other' })

    await expect(request).rejects.toBeInstanceOf(CmkApiError)
  })
})
