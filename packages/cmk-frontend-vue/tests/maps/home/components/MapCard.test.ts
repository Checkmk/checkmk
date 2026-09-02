/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapCard from '@/maps/home/components/MapCard.vue'
import type { MapRead } from '@/maps/types/api'

import { aConnection, aListedMap, newMapView } from '../../support/fixtures'
import {
  aTicket,
  fakeMapsServices,
  fullCapabilities,
  provideServices
} from '../../support/services'

function listed(over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name: 'prod', alias: 'Production', object_count: 4, ...over })
}

/**
 * Renders the card. ``connectionIds`` is what the installation has configured —
 * the card names a map's own connection only where there is more than one.
 */
async function renderCard(
  map: MapRead,
  capabilities = fullCapabilities(),
  connectionIds = ['live_1', 'live_2']
) {
  const services = fakeMapsServices({}, aTicket({ user_id: 'me', capabilities }))
  await services.auth.init()
  services.connections.connections.value = connectionIds.map((id) => aConnection(id))
  return render(MapCard, { ...provideServices(services), props: { map } })
}

const READER = fullCapabilities({ configure: false, may_edit: false })

describe('MapCard', () => {
  it('names the map and links to it', async () => {
    await renderCard(listed())
    const link = screen.getByRole('link', { name: /Production/ })
    expect(link).toHaveAttribute('href', expect.stringContaining('name=prod'))
  })

  it('falls back to the id when a map has no display name', async () => {
    await renderCard(listed({ alias: '' }))
    expect(screen.getByRole('link', { name: /prod/ })).toBeInTheDocument()
  })

  it('says what kind of map it is', async () => {
    await renderCard(listed({ view: newMapView('worldmap') }))
    expect(screen.getByText('Geo map')).toBeInTheDocument()
  })

  it('counts the objects a map has placed', async () => {
    await renderCard(listed({ object_count: 4 }))
    expect(screen.getByText('4 objects')).toBeInTheDocument()
  })

  it('says the contents are live where a count would be wrong', async () => {
    await renderCard(listed({ view: newMapView('radar') }))
    expect(screen.getByText('live contents')).toBeInTheDocument()
  })

  it('points out that a map is shared', async () => {
    await renderCard(listed({ public: true }))
    expect(screen.getByText('Published')).toBeInTheDocument()
  })

  it('names the private default too, next to the other facts', async () => {
    await renderCard(listed({ public: false }))
    expect(screen.getByText('Private')).toBeInTheDocument()
  })

  it('shows an administrator the connection and the management flags', async () => {
    await renderCard(listed({ show_in_lists: false, rotation_interval: 30 }))
    expect(screen.getByText('live_1')).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Map flags' })).toHaveTextContent('Hidden')
    expect(screen.getByTitle('Rotates every 30 seconds')).toBeInTheDocument()
  })

  it('leaves the flag row out where a map carries no flag at all', async () => {
    await renderCard(listed())
    expect(screen.queryByRole('group', { name: 'Map flags' })).not.toBeInTheDocument()
  })

  it("keeps connection and flags out of a plain reader's card", async () => {
    await renderCard(listed({ show_in_lists: false }), READER)
    expect(screen.queryByText('live_1')).not.toBeInTheDocument()
    expect(screen.queryByText('Hidden')).not.toBeInTheDocument()
  })

  it('leaves the connection out where the installation has only one', async () => {
    await renderCard(listed(), fullCapabilities(), ['live_1'])
    expect(screen.queryByText('live_1')).not.toBeInTheDocument()
  })
})
