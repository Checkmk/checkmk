/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { expect, test } from 'vitest'

import type { HostRef } from '@/monitoring/shared/api/types'
import { useScheduleHostDowntimeAction } from '@/monitoring/shared/components/action/actions/scheduleHostDowntime'

const WEB_1: HostRef[] = [{ name: 'web-1', site_id: 'local' }]

// web-1 has one child host, which the site puts in downtime too when the request says so.
useMswServer(
  restApiHttp.post('/monitor/hosts/actions/schedule_downtime', async ({ request, response }) => {
    const body = await request.json()
    return response(200).json({
      scheduled: body.hosts.length + (body.include_child_hosts ? 1 : 0)
    })
  })
)

test('sends the child hosts along only when the form asks for them', async () => {
  const downtime = useScheduleHostDowntimeAction([], [], null)

  const result = await downtime.perform(WEB_1, {
    ...downtime.defaultValues(),
    includeChildHosts: false
  })

  expect(result.message).toBe('Scheduled a downtime for 1 host')
})

test('counts the hosts the site put in downtime, not the hosts selected', async () => {
  const downtime = useScheduleHostDowntimeAction([], [], null)

  const result = await downtime.perform(WEB_1, {
    ...downtime.defaultValues(),
    includeChildHosts: true
  })

  expect(result.message).toBe('Scheduled a downtime for 2 hosts')
})
