/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { expect, test, vi } from 'vitest'

import type { HostRef } from '@/monitoring/shared/api/types'
import { useAcknowledgeHostsAction } from '@/monitoring/shared/components/action/actions/acknowledgeHosts'

const NO_LINKS = { presetsUrl: null, notificationRulesUrl: null }
const DEFAULTS = { sticky: false, persistent: false, notify: true, expireSeconds: 3600 }

function respondAcknowledged(acknowledged: number): void {
  vi.spyOn(client, 'POST').mockResolvedValue({
    data: { acknowledged },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
}

function hosts(...names: string[]): HostRef[] {
  return names.map((name) => ({ name, site_id: 'local' }))
}

test('the success message names no count, only the plural', async () => {
  respondAcknowledged(3)
  const action = useAcknowledgeHostsAction(NO_LINKS, DEFAULTS)

  const feedback = await action.perform(hosts('down-1', 'down-2', 'down-3'), action.defaultValues())

  expect(feedback).toEqual({
    variant: 'success',
    message: 'Acknowledged the problems of the selected hosts'
  })
})

test('the success message follows the count the server acknowledged', async () => {
  respondAcknowledged(1)
  const action = useAcknowledgeHostsAction(NO_LINKS, DEFAULTS)

  const feedback = await action.perform(hosts('down-1', 'down-2'), action.defaultValues())

  expect(feedback).toEqual({
    variant: 'success',
    message: 'Acknowledged the problem of the selected host'
  })
})
