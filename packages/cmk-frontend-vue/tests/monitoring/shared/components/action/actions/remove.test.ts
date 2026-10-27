/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { useRemoveHostAcknowledgementsAction } from '@/monitoring/all-hosts/actions/removeHostAcknowledgements'
import { rowsToActOn } from '@/monitoring/shared/components/action/actions/remove'
import { useRemoveServiceAcknowledgementsAction } from '@/monitoring/shared/components/action/actions/removeServiceAcknowledgements'

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

const ROWS = [
  { name: 'acked', modes: [{ id: 'acknowledged' }] },
  { name: 'down', modes: [{ id: 'downtime' }, { id: 'comments' }] },
  { name: 'plain' }
]

test('a removal acts only on the rows having something to remove', () => {
  expect(rowsToActOn(ROWS, 'remove_acknowledgments').map((row) => row.name)).toEqual(['acked'])
})

test('any other action acts on all rows', () => {
  expect(rowsToActOn(ROWS, 'add_comment')).toBe(ROWS)
})
