/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentInventory from '@/dashboard/components/DashboardContent/figures/DashboardContentInventory.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import type { InventoryAttribute, InventoryContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const ENDPOINT = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/compute-inventory/invoke`

const ATTRIBUTE: InventoryAttribute = {
  links: [],
  link_properties: { links: [] },
  value: '8'
}

const CONTENT: InventoryContent = {
  type: 'inventory',
  path: '.hardware.cpu.cores',
  contextual_link: { type: 'default' }
}

let answer: () => Response = () =>
  HttpResponse.json({ domainType: 'widget-compute', value: ATTRIBUTE })
let requests: unknown[] = []

useMswServer(
  http.post(ENDPOINT, async ({ request }) => {
    requests.push(await request.json())
    return answer()
  })
)

async function renderWidget(props: ContentProps<InventoryContent> = makeContentProps(CONTENT)) {
  const rendered = render(DashboardContentInventory, { props })
  await nextTick()
  deliverSize(400, 200)
  return rendered
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})
afterEach(() => {
  answer = () => HttpResponse.json({ domainType: 'widget-compute', value: ATTRIBUTE })
  requests = []
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})

describe('DashboardContentInventory', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    await waitFor(() =>
      expect(requests).toEqual([{ source: { type: 'explicit', content: CONTENT, context: {} } }])
    )
  })

  it('draws the attribute as delivered by the backend', async () => {
    await renderWidget()

    expect(await screen.findByText('8')).toBeInTheDocument()
  })

  it('fetches again on a refresh tick', async () => {
    const { rerender } = await renderWidget()
    await screen.findByText('8')

    await rerender(makeContentProps(CONTENT, { tick: 1 }))

    await waitFor(() => expect(requests).toHaveLength(2))
  })

  it('shows the no-data notice on a 404', async () => {
    answer = () => HttpResponse.json({ title: 'No data available', status: 404 }, { status: 404 })

    await renderWidget()

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })
})
