/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import type { ServiceRef } from '@/monitoring/shared/api/types'
import { CHECK_POLL_INTERVAL_MS } from '@/monitoring/shared/components/action/actions/reschedule'
import { useRescheduleServicesAction } from '@/monitoring/shared/components/action/actions/rescheduleServices'

const SCHEDULED_AT = 1_800_000_000

beforeEach(() => {
  vi.useFakeTimers()
  vi.spyOn(client, 'POST').mockResolvedValue({
    data: { rescheduled: 1, scheduled_at: SCHEDULED_AT, wait_timeout: 10 },
    error: undefined,
    response: new Response()
  } as never)
  vi.spyOn(client, 'GET').mockResolvedValue({
    data: { last_check: SCHEDULED_AT },
    error: undefined,
    response: new Response()
  } as never)
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

function serviceOfWeb1(description: string): ServiceRef {
  return { host: { site_id: 'local', name: 'web-1' }, description }
}

async function rescheduleOne(service: ServiceRef): Promise<unknown> {
  const action = useRescheduleServicesAction()
  const feedback = action.perform([service], action.defaultValues())
  await vi.advanceTimersByTimeAsync(CHECK_POLL_INTERVAL_MS)
  return (await feedback).message
}

test('names the service whose check has run', async () => {
  expect(await rescheduleOne(serviceOfWeb1('HTTP'))).toBe('The check of "HTTP" on web-1 has run')
})

test('tells that the "Check_MK" service updates the services that are its byproducts', async () => {
  expect(await rescheduleOne(serviceOfWeb1('Check_MK'))).toBe(
    'The "Check_MK" service of web-1 has run, and with it the services it updates'
  )
})
