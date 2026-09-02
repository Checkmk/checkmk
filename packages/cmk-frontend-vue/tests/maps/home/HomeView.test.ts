/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeView from '@/maps/home/HomeView.vue'
import type { MapRead } from '@/maps/types/api'

import { aListedMap } from '../support/fixtures'
import { aTicket, fakeMapsServices, fullCapabilities, provideServices } from '../support/services'

function listed(name: string, over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name, alias: name, ...over })
}

let services: ReturnType<typeof fakeMapsServices>

async function renderHome(maps: MapRead[]) {
  services = fakeMapsServices({}, aTicket({ user_id: 'me', capabilities: fullCapabilities() }))
  await services.auth.init()
  vi.spyOn(services.maps, 'fetchMaps').mockImplementation(async () => {
    services.maps.maps.value = maps
  })
  const result = render(HomeView, provideServices(services))
  await waitFor(() => expect(services.maps.fetchMaps).toHaveBeenCalled())
  return result
}

beforeEach(() => {
  localStorage.clear()
})

describe('HomeView', () => {
  it('reads the list when it opens and shows a card per map', async () => {
    await renderHome([listed('prod'), listed('lab')])
    expect(screen.getByRole('link', { name: /prod/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /lab/ })).toBeInTheDocument()
  })

  it('explains an empty site instead of showing an empty grid', async () => {
    await renderHome([])
    expect(screen.getByText('No maps configured.')).toBeInTheDocument()
  })

  it('offers no in-page controls while there is nothing to filter', async () => {
    await renderHome([])
    expect(screen.queryByPlaceholderText('Search maps…')).not.toBeInTheDocument()
  })

  it('leaves the scope filter out while every map has the same owner', async () => {
    await renderHome([listed('prod'), listed('lab')])
    expect(screen.getByPlaceholderText('Search maps…')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Built-in' })).not.toBeInTheDocument()
  })

  it('offers the scope filter once maps of several owners are listed', async () => {
    await renderHome([listed('prod'), listed('demo', { is_builtin: true })])
    expect(screen.getByRole('button', { name: 'Built-in' })).toBeInTheDocument()
  })

  it('marks the scope the list is narrowed to', async () => {
    await renderHome([listed('prod'), listed('demo', { is_builtin: true })])
    await userEvent.click(screen.getByRole('button', { name: 'Built-in' }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Built-in' })).toHaveAttribute(
        'aria-pressed',
        'true'
      )
    )
  })

  it('narrows the list to the chosen scope', async () => {
    await renderHome([listed('prod'), listed('demo', { is_builtin: true })])
    await userEvent.click(screen.getByRole('button', { name: 'Built-in' }))
    await waitFor(() =>
      expect(screen.queryByRole('link', { name: /prod/ })).not.toBeInTheDocument()
    )
  })

  it('explains a search that matched nothing, in either list mode', async () => {
    await renderHome([listed('prod')])
    const search = screen.getByPlaceholderText('Search maps…')
    await userEvent.type(search, 'nope')
    await waitFor(() => expect(screen.getByText('No maps match "nope".')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Table' }))
    await waitFor(() => expect(screen.getByText('No maps match "nope".')).toBeInTheDocument())
  })

  it('opens the create dialog from the page header', async () => {
    await renderHome([listed('prod')])

    await userEvent.click(screen.getByRole('button', { name: 'Add map' }))
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument())
  })

  it("puts the cursor in the new map's ID field, so it can be typed right away", async () => {
    await renderHome([listed('prod')])

    await userEvent.click(screen.getByRole('button', { name: 'Add map' }))
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Map ID')))
  })

  it('switches the list to the table on the view switch', async () => {
    await renderHome([listed('prod')])
    expect(screen.queryByRole('columnheader')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Table' }))
    await waitFor(() =>
      expect(screen.getByRole('columnheader', { name: /Name/ })).toBeInTheDocument()
    )
  })
})
