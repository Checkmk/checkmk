/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, expect, test, vi } from 'vitest'

import type { HostRef } from '@/monitoring/shared/api/types'
import GraphsLink from '@/monitoring/shared/components/graphs/GraphsLink.vue'

const HOST: HostRef = { site_id: 'local', name: 'web-server-01' }

afterEach(() => {
  vi.restoreAllMocks()
})

test('asks for the graphs only once the preview opens, not for every link a table renders', async () => {
  const post = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { graphs: [], no_data_message: null },
    response: new Response(null, { status: 200 })
  } as never)
  render(GraphsLink, { props: { host: HOST, service: 'CPU load', href: 'view.py' } })
  const link = screen.getByRole('link', { name: 'Show the graphs of service CPU load' })
  expect(post).not.toHaveBeenCalled()

  await userEvent.hover(link)

  await vi.waitUntil(() => post.mock.calls.length > 0)
})

test('names the host in a link to the graphs of the host itself', () => {
  render(GraphsLink, { props: { host: HOST, href: 'view.py' } })

  expect(
    screen.getByRole('link', { name: 'Show the graphs of host web-server-01' })
  ).toHaveAttribute('href', 'view.py')
})
