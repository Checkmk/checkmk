/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { useResetHostModifiedAttributesAction } from '@/monitoring/shared/components/action/actions/resetHostModifiedAttributes'
import { useResetServiceModifiedAttributesAction } from '@/monitoring/shared/components/action/actions/resetServiceModifiedAttributes'

const DB = { name: 'db-1', site_id: 'local' }

beforeEach(() => {
  vi.spyOn(client, 'POST').mockResolvedValue({
    data: { modified: 1 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('asks to confirm resetting the modified attributes', () => {
  const { title, confirm } = useResetHostModifiedAttributesAction()

  expect([title, confirm?.submitLabel(2)]).toEqual([
    'Reset modified attributes',
    'Reset attributes'
  ])
  expect(confirm?.detail(2, [])).toBe(
    "Resets the commands 'Enable/disable active checks', 'Enable/disable passive checks' and 'Enable/disable notifications' to the default state."
  )
})

test('says the modified attributes of the selected host were reset', async () => {
  expect(await useResetHostModifiedAttributesAction().perform([DB], {})).toEqual({
    variant: 'success',
    message: 'Modified attributes are reset for the selected host'
  })
})

test('says the modified attributes of the selected services were reset', async () => {
  const services = [
    { host: DB, description: 'CPU load' },
    { host: DB, description: 'Memory' }
  ]

  expect(await useResetServiceModifiedAttributesAction().perform(services, {})).toEqual({
    variant: 'success',
    message: 'Modified attributes are reset for the selected services'
  })
})
