/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'

import PresentationDataPanel from '@/maps/map/presentation/components/PresentationDataPanel.vue'

import { useMswServer } from '../../../support/http'
import { mapsGlobal } from '../../../support/services'

const API_BASE = `${location.protocol}//${location.host}/api/internal`

// Like Checkmk's host autocompleter: at most 200 names, plus one past that when
// there are more. The site has 150 generic hosts, exactly 200 blades and heute.
const LIMIT = 200
const HOSTS = [
  ...Array.from({ length: 150 }, (_, i) => `srv-${i}`),
  ...Array.from({ length: 200 }, (_, i) => `blade-${i}`),
  'heute'
]

let answerHeld: Promise<void> | null = null

useMswServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ request }) => {
    const { value } = (await request.json()) as { value: string }
    await answerHeld
    const choices = HOSTS.filter((host) => host.includes(value))
      .slice(0, LIMIT + 1)
      .map((host) => ({ id: host, value: host }))
    return HttpResponse.json({ choices })
  })
)

afterEach(() => {
  cleanup()
  answerHeld = null
})

function renderPanel() {
  return render(PresentationDataPanel, {
    props: { connectionId: 'local', elements: [], states: {} },
    global: mapsGlobal()
  })
}

const CAP_NOTE = /keep typing to narrow results/

describe('PresentationDataPanel', () => {
  it('finds a host beyond the first page as the operator types', async () => {
    renderPanel()
    expect(await screen.findByText('srv-0')).toBeInTheDocument()
    expect(screen.queryByText('heute')).toBeNull()

    await userEvent.type(screen.getByPlaceholderText('Search hosts…'), 'heu')

    expect(await screen.findByText('heute')).toBeInTheDocument()
    expect(screen.queryByText('srv-0')).toBeNull()
  })

  it('says the list is cut only when there are more matches than shown', async () => {
    renderPanel()
    expect(await screen.findByText(CAP_NOTE)).toBeInTheDocument()

    // Exactly as many blades as the limit: the list is complete.
    await userEvent.type(screen.getByPlaceholderText('Search hosts…'), 'blade')

    await waitFor(() => expect(screen.queryByText('srv-0')).toBeNull())
    expect(screen.getByText('blade-0')).toBeInTheDocument()
    expect(screen.queryByText(CAP_NOTE)).toBeNull()
  })

  it('keeps the rows up while a narrower search loads', async () => {
    renderPanel()
    expect(await screen.findByText('srv-0')).toBeInTheDocument()

    let answer: () => void = () => {}
    answerHeld = new Promise((resolve) => {
      answer = resolve
    })
    await userEvent.type(screen.getByPlaceholderText('Search hosts…'), 'heu')

    const list = screen.getByText('srv-0').closest('[aria-busy]')
    await waitFor(() => expect(list).toHaveAttribute('aria-busy', 'true'))
    expect(screen.getByText('srv-0')).toBeInTheDocument()

    answer()
    expect(await screen.findByText('heute')).toBeInTheDocument()
    expect(list).toHaveAttribute('aria-busy', 'false')
  })
})
