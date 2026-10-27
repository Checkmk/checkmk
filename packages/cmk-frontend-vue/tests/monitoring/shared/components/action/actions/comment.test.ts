/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'

import { useCommentHostsAction } from '@/monitoring/all-hosts/actions/commentHosts'
import { useCommentServicesAction } from '@/monitoring/shared/components/action/actions/commentServices'

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

test('says the comment was added to the selected host', async () => {
  const action = useCommentHostsAction()

  expect(await action.perform([HOST], { comment: 'Disk swap planned' })).toEqual({
    variant: 'success',
    message: 'Added comment to the selected host'
  })
})

test('says the comments were added to the selected services', async () => {
  const action = useCommentServicesAction()

  expect(
    await action.perform(
      [
        { host: HOST, description: 'CPU load' },
        { host: HOST, description: 'Memory' }
      ],
      { comment: 'Known spike' }
    )
  ).toEqual({
    variant: 'success',
    message: 'Added comments to the selected services'
  })
})

test('sends the comment without surrounding blanks', async () => {
  const action = useCommentHostsAction()

  await action.perform([HOST], { comment: '  Disk swap planned ' })

  expect(postSpy.mock.lastCall[1].body.comment).toBe('Disk swap planned')
})

test('reports a refused comment as an error', async () => {
  postSpy.mockResolvedValue({
    data: undefined,
    error: {},
    response: new Response(null, { status: 500 })
  } as never)
  const action = useCommentHostsAction()

  expect(await action.perform([HOST], { comment: 'Disk swap planned' })).toMatchObject({
    variant: 'error',
    heading: 'Could not add the comments to the selected hosts'
  })
})
