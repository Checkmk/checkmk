/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { rowsToActOn } from '@/monitoring/shared/components/action/actions/remove'
import { useRemoveHostAcknowledgementsAction } from '@/monitoring/shared/components/action/actions/removeHostAcknowledgements'
import { useRemoveHostDowntimesAction } from '@/monitoring/shared/components/action/actions/removeHostDowntimes'
import { useRemoveServiceAcknowledgementsAction } from '@/monitoring/shared/components/action/actions/removeServiceAcknowledgements'
import { useRemoveServiceDowntimesAction } from '@/monitoring/shared/components/action/actions/removeServiceDowntimes'

const HOST = { name: 'db-1', site_id: 'local' }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: undefined,
    error: undefined,
    response: new Response(null, { status: 204 })
  } as never)
})

test('says the acknowledgement of the selected host was removed', async () => {
  expect(await useRemoveHostAcknowledgementsAction().perform([HOST], {})).toEqual({
    variant: 'success',
    message: 'Removed acknowledgement of the selected host'
  })
})

test('says the downtimes of the selected services were removed', async () => {
  expect(
    await useRemoveServiceDowntimesAction().perform(
      [
        { host: HOST, description: 'CPU load' },
        { host: HOST, description: 'Memory' }
      ],
      {}
    )
  ).toEqual({
    variant: 'success',
    message: 'Removed downtimes of the selected services'
  })
})

test('reports a refused removal as an error', async () => {
  postSpy.mockResolvedValue({
    data: undefined,
    error: {},
    response: new Response(null, { status: 403 })
  } as never)

  expect(
    await useRemoveServiceAcknowledgementsAction().perform(
      [{ host: HOST, description: 'CPU load' }],
      {}
    )
  ).toMatchObject({
    variant: 'error',
    heading: 'Could not remove the acknowledgements of the selected services'
  })
})

test('asks to confirm the acknowledgements it removes', () => {
  const { confirm } = useRemoveHostAcknowledgementsAction()

  expect(confirm?.detail(2)).toBe('Acknowledgements: 2')
  expect(confirm?.submitLabel(1)).toBe('Remove acknowledgements')
})

test('asks to confirm the downtimes it removes', () => {
  const { confirm } = useRemoveHostDowntimesAction()

  expect(confirm?.detail(3)).toBe('Downtimes: 3')
  expect(confirm?.submitLabel(1)).toBe('Remove downtimes')
})

const ROWS = [
  { name: 'acked', modes: [{ id: 'acknowledged' }] },
  { name: 'down', modes: [{ id: 'downtime' }, { id: 'comments' }] },
  { name: 'plain' }
]

test('a removal acts only on the rows having something to remove', () => {
  expect(rowsToActOn(ROWS, 'remove_acknowledgments').map((row) => row.name)).toEqual(['acked'])
  expect(rowsToActOn(ROWS, 'remove_downtimes_hosts_services').map((row) => row.name)).toEqual([
    'down'
  ])
})

test('any other action acts on all rows', () => {
  expect(rowsToActOn(ROWS, 'add_comment')).toBe(ROWS)
})
