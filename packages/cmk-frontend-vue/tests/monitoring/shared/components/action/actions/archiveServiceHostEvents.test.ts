/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { useArchiveServiceHostEventsAction } from '@/monitoring/shared/components/action/actions/archiveServiceHostEvents'

const DB = { name: 'db-1', site_id: 'local' }
const WEB = { name: 'web-1', site_id: 'local' }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { modified: 1, archived: 1 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('archives the events of each host of the selected services once', async () => {
  const services = [
    { host: DB, description: 'CPU load' },
    { host: DB, description: 'Memory' }
  ]

  expect(await useArchiveServiceHostEventsAction().perform(services, {})).toEqual({
    variant: 'success',
    message: 'Events are archived for the selected host'
  })
  expect(postSpy.mock.lastCall[1].body).toEqual({ hosts: [DB] })
})

test('names the hosts, not the services, when asking to archive', () => {
  const { confirm } = useArchiveServiceHostEventsAction()
  const services = [
    { host: DB, description: 'CPU load' },
    { host: WEB, description: 'CPU load' }
  ]

  expect(confirm?.detail(2, services)).toBe(
    'All events of the hosts will be removed from the open events list. You can still access them in the archive.'
  )
  expect(confirm?.submitLabel(2)).toBe('Archive events')
})
