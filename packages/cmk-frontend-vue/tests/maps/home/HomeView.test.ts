/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeView from '@/maps/home/HomeView.vue'
import { MAP_LIST_LAYOUT } from '@/maps/home/composables/useMapListViewMode'
import type { MapListView, MapRead } from '@/maps/types/api'

import { aListedMap } from '../support/fixtures'
import { triggerPageMenu } from '../support/pageMenu'
import { aTicket, fakeMapsServices, fullCapabilities, provideServices } from '../support/services'

function listed(name: string, over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name, alias: name, ...over })
}

let services: ReturnType<typeof fakeMapsServices>

async function renderHome(
  maps: MapRead[],
  {
    capabilities = fullCapabilities(),
    layout = 'cards'
  }: { capabilities?: ReturnType<typeof fullCapabilities>; layout?: MapListView } = {}
) {
  services = fakeMapsServices({}, aTicket({ user_id: 'me', capabilities }))
  await services.auth.init()
  vi.spyOn(services.maps, 'fetchMaps').mockImplementation(async () => {
    services.maps.maps.value = maps
  })
  const provided = provideServices(services).global.provide
  const result = render(HomeView, {
    global: { provide: { ...provided, [MAP_LIST_LAYOUT as symbol]: layout } }
  })
  await waitFor(() => expect(services.maps.fetchMaps).toHaveBeenCalled())
  return result
}

beforeEach(() => {
  window.history.replaceState({}, '', '/site/check_mk/maps.py')
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

  it('leaves the scope filter out while every map has the same owner', async () => {
    await renderHome([listed('prod'), listed('lab')])
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

  it.each<MapListView>(['cards', 'table'])(
    'explains a search that matched nothing in the %s layout',
    async (layout) => {
      await renderHome([listed('prod')], { layout })
      await userEvent.type(screen.getByPlaceholderText('Search maps…'), 'nope')
      await waitFor(() => expect(screen.getByText('No maps match "nope".')).toBeInTheDocument())
    }
  )

  it('keeps the search in the page URL, so the way back from a map keeps it', async () => {
    await renderHome([listed('prod'), listed('lab')])
    await userEvent.type(screen.getByPlaceholderText('Search maps…'), 'lab')
    await waitFor(() => expect(screen.queryByRole('link', { name: /prod/ })).toBeNull())
    await waitFor(() =>
      expect(new URLSearchParams(window.location.search).get('search')).toBe('lab')
    )
  })

  it('starts from the search the page was loaded with', async () => {
    window.history.replaceState({}, '', '/site/check_mk/maps.py?search=lab')
    await renderHome([listed('prod'), listed('lab')])
    await waitFor(() => expect(screen.queryByRole('link', { name: /prod/ })).toBeNull())
    expect(screen.getByRole('link', { name: /lab/ })).toBeInTheDocument()
  })

  it('keeps the scope in the page URL', async () => {
    await renderHome([listed('prod'), listed('demo', { is_builtin: true })])
    await userEvent.click(screen.getByRole('button', { name: 'Built-in' }))
    expect(new URLSearchParams(window.location.search).get('scope')).toBe('builtin')
  })

  it('opens the create dialog from the page menu', async () => {
    await renderHome([listed('prod')])

    triggerPageMenu('create')
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument())
  })

  it("puts the cursor in the new map's name, so it can be typed right away", async () => {
    await renderHome([listed('prod')])

    triggerPageMenu('create')
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Display name')))
  })

  it('fills the map ID in from the display name', async () => {
    await renderHome([listed('prod')])

    triggerPageMenu('create')
    await userEvent.type(await screen.findByLabelText('Display name'), 'Büro – Straße')
    expect(screen.getByLabelText('Map ID')).toHaveValue('buro-strasse')
  })

  it('says so when a display name leaves nothing to fill an ID in from', async () => {
    await renderHome([listed('prod')])

    triggerPageMenu('create')
    await userEvent.type(await screen.findByLabelText('Display name'), '東京')
    expect(screen.getByText(/no letters or digits to fill in an ID from/)).toBeInTheDocument()
  })

  it('fills the map ID in again from the display name once it is emptied', async () => {
    await renderHome([listed('prod')])

    triggerPageMenu('create')
    await userEvent.type(await screen.findByLabelText('Display name'), 'My map')
    const mapId = screen.getByLabelText('Map ID')
    await userEvent.type(mapId, '-x')
    await userEvent.clear(mapId)
    expect(mapId).toHaveValue('my-map')
    expect(screen.queryByText(/no letters or digits to fill in an ID from/)).toBeNull()
  })

  it('cuts an ID filled in from a long display name to fit', async () => {
    await renderHome([listed('prod')])
    services.settings.mapNameMaxLength.value = 64

    triggerPageMenu('create')
    await userEvent.type(await screen.findByLabelText('Display name'), 'x'.repeat(70))
    expect(screen.getByLabelText('Map ID')).toHaveValue('x'.repeat(64))
    expect(screen.queryByText(/too long/)).toBeNull()
  })

  it('shows the layout the page was handed', async () => {
    await renderHome([listed('prod')], { layout: 'table' })
    expect(await screen.findByRole('columnheader', { name: /Title/ })).toBeInTheDocument()
  })

  it('offers deleting the selection to a user who may only delete some maps', async () => {
    await renderHome([listed('prod', { can_delete: true })], {
      capabilities: fullCapabilities({ may_edit: false, configure: false }),
      layout: 'table'
    })

    await userEvent.click(await screen.findByRole('checkbox', { name: 'Select prod' }))

    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
  })
})

async function cardOf(name: string): Promise<HTMLElement> {
  const link = await screen.findByRole('link', { name })
  const card = link.closest<HTMLElement>('[role="listitem"]')
  if (!card) {
    throw new Error(`no card for ${name}`)
  }
  return card
}

/** jsdom has no DataTransfer; this is the part of it a drag touches. */
function dragData(dropEffect: DataTransfer['dropEffect'] = 'move') {
  return {
    dataTransfer: {
      dropEffect,
      effectAllowed: 'uninitialized',
      setData: vi.fn(),
      setDragImage: vi.fn()
    }
  }
}

describe('HomeView — reordering cards', () => {
  const mine = (name: string): MapRead => listed(name, { owner: 'me', can_edit: true })

  it('offers your own maps for dragging while built-in ones are listed too', async () => {
    await renderHome([mine('first'), listed('demo', { is_builtin: true })])
    expect(await cardOf('first')).toHaveAttribute('draggable', 'true')
    expect(await cardOf('demo')).not.toHaveAttribute('draggable', 'true')
  })

  it('stores the order your maps were dragged into', async () => {
    await renderHome([mine('first'), mine('second'), listed('demo', { is_builtin: true })])
    const reorder = vi.spyOn(services.maps, 'reorderMaps').mockResolvedValue()

    const second = await cardOf('second')
    await fireEvent.dragStart(second, dragData())
    await fireEvent.dragOver(await cardOf('first'), dragData())
    await fireEvent.dragEnd(second, dragData('move'))

    expect(reorder).toHaveBeenCalledWith([
      { name: 'second', sort_order: 0 },
      { name: 'first', sort_order: 1 }
    ])
  })
})
