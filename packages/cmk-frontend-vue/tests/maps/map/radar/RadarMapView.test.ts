/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import RadarMapView from '@/maps/map/radar/RadarMapView.vue'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aMap, aState, newMapView } from '../../support/fixtures'
import { fakeMapsServices, provideServices } from '../../support/services'

const sampleStates: Record<string, ObjectState> = {
  'web-01': aState({ object_id: 'web-01', type: 'host', state: 'UP', output: 'PING OK' }),
  'db-01;Disk usage': aState({
    object_id: 'db-01;Disk usage',
    type: 'service',
    state: 'CRITICAL',
    output: 'Disk full'
  }),
  'app-01': aState({ object_id: 'app-01', type: 'host', state: 'WARNING', output: 'Load high' })
}

/** A radar map's content is the state stream, so a case sets that up. */
function renderRadar(
  states: Record<string, ObjectState> = sampleStates,
  {
    /** Whether a state snapshot has arrived at all. */
    snapshotArrived = true,
    /** What the daemon reported about its monitoring connection. */
    connected = true,
    /** Why reading state failed, if it did. */
    loadError = null as string | null,
    preview = false,
    /** Stubbed out where a case is about how many cards there are, not what is on them. */
    stubCards = false
  } = {}
) {
  const services = fakeMapsServices()
  services.states.states.value = states
  services.states.connected.value = connected
  services.states.lastUpdate.value = snapshotArrived ? 1_700_000_000 : null
  services.states.loadError.value = loadError
  // The object-click emit is the view's click contract; capture it through a
  // real handler on a host wrapper instead of inspecting emitted events.
  const clicked = ref<MapElement | null>(null)
  const config = aMap({ view: newMapView('radar') })
  const { container } = render(
    defineComponent({
      components: { RadarMapView },
      setup() {
        const onObjectClick = (object: MapElement) => {
          clicked.value = object
        }
        return { config, onObjectClick, preview }
      },
      template: `<RadarMapView
        :config="config"
        :error="null"
        :preview="preview"
        filter-needle=""
        :problems-only="false"
        @object-click="onObjectClick"
      />`
    }),
    {
      global: {
        ...provideServices(services).global,
        stubs: { MapSearch: true, CmkLoading: true, ...(stubCards ? { RadarCard: true } : {}) }
      }
    }
  )
  return {
    services,
    clicked,
    isLoading: () => container.querySelector('cmk-loading-stub') !== null,
    cardCount: () => container.querySelectorAll('radar-card-stub').length
  }
}

describe('RadarMapView', () => {
  it('renders one accessible card per state, worst state first', () => {
    renderRadar()

    // Card order + "<name>, <state word>" accessible names pin the severity
    // sort: CRITICAL before WARNING before UP.
    const cards = screen.getAllByRole('button')
    expect(cards.map((card) => card.getAttribute('aria-label'))).toEqual([
      'db-01 · Disk usage, Critical',
      'app-01, Warning',
      'web-01, Up'
    ])
    expect(screen.getByText(/3 objects/)).toBeInTheDocument()
  })

  it('shows the summary legend with per-state counts, worst first', () => {
    renderRadar()

    const critical = screen.getByText(/1 Critical/)
    const warning = screen.getByText(/1 Warning/)
    const up = screen.getByText(/1 Up/)
    // Document order pins the legend's severity sort.
    expect(
      critical.compareDocumentPosition(warning) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy()
    expect(warning.compareDocumentPosition(up) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('renders the empty state when no objects match', () => {
    renderRadar({})

    expect(screen.queryAllByRole('button')).toHaveLength(0)
    expect(screen.getByText('No objects found')).toBeInTheDocument()
  })

  it('renders the empty state for an empty snapshot, which reports no connection', () => {
    // The daemon derives `connection_ok` from the states it found, so every
    // empty result arrives disconnected -- a site without hosts must still
    // reach the empty state rather than spin.
    const { isLoading } = renderRadar({}, { connected: false })

    expect(isLoading()).toBe(false)
    expect(screen.getByText('No objects found')).toBeInTheDocument()
  })

  it('keeps loading while no snapshot has arrived yet', () => {
    const { isLoading } = renderRadar({}, { snapshotArrived: false, connected: false })

    expect(isLoading()).toBe(true)
    expect(screen.queryByText('No objects found')).toBeNull()
  })

  it('reports why the first read failed instead of spinning on for good', () => {
    // Nothing came back, so there is no last known state to fall back on: the
    // reason has to take the map's place, or the spinner reads as "still loading".
    const { isLoading } = renderRadar(
      {},
      { snapshotArrived: false, connected: false, loadError: 'Daemon unreachable' }
    )

    expect(isLoading()).toBe(false)
    expect(screen.getByText('Daemon unreachable')).toBeInTheDocument()
  })

  it('warns that the connection dropped while it keeps the last known states up', () => {
    renderRadar(sampleStates, { connected: false })

    expect(screen.getByText('Connection lost — showing last known state')).toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(3)
  })

  it('names the sites that stopped answering', () => {
    const { services } = renderRadar(sampleStates)
    services.states.deadSites.value = ['remote-1']

    return vi.waitFor(() =>
      expect(
        screen.getByText('Site unreachable: remote-1 — showing last known state for its hosts')
      ).toBeInTheDocument()
    )
  })

  it('caps the cards it draws and says how many it left out', () => {
    const many: Record<string, ObjectState> = {}
    for (let i = 0; i < 520; i++) {
      const id = `host-${String(i).padStart(3, '0')}`
      many[id] = aState({ object_id: id, type: 'host', state: 'UP' })
    }

    // The cards themselves are stubbed: the case is about how many of them the
    // view draws, and 520 real ones make it the slowest test in the suite.
    const { cardCount } = renderRadar(many, { stubCards: true })

    expect(cardCount()).toBe(500)
    expect(screen.getByText(/520 objects/)).toBeInTheDocument()
    expect(screen.getByText('+20 more — refine the filter to see them')).toBeInTheDocument()
  })

  it('tallies every match in the legend, not just the cards that fit', () => {
    const many: Record<string, ObjectState> = {
      'db-01;Disk usage': aState({
        object_id: 'db-01;Disk usage',
        type: 'service',
        state: 'CRITICAL'
      })
    }
    for (let i = 0; i < 20; i++) {
      const id = `host-${String(i).padStart(2, '0')}`
      many[id] = aState({ object_id: id, type: 'host', state: 'UP' })
    }

    // The preview shows 12 of 21 cards; the one CRITICAL fits, but the tally
    // for the 20 UPs must count all of them rather than the 11 on screen.
    renderRadar(many, { preview: true })

    expect(screen.getByText(/20 Up/)).toBeInTheDocument()
  })

  it('says "1 object" for a single match', () => {
    renderRadar({ 'web-01': aState({ object_id: 'web-01', type: 'host', state: 'UP' }) })

    expect(screen.getByText(/1 object(?!s)/)).toBeInTheDocument()
  })

  it('reports a clicked card as a synthesized map object', async () => {
    const user = userEvent.setup()
    const { clicked } = renderRadar()

    await user.click(screen.getByRole('button', { name: /db-01 · Disk usage/ }))

    expect(clicked.value).toMatchObject({
      type: 'service',
      host_name: 'db-01',
      service_description: 'Disk usage'
    })
  })

  it('activates a card via keyboard: focus + Enter fires the click contract', async () => {
    const user = userEvent.setup()
    const { clicked } = renderRadar()

    const card = screen.getByRole('button', { name: 'web-01, Up' })
    card.focus()
    await user.keyboard('{Enter}')

    expect(clicked.value).toMatchObject({ type: 'host', host_name: 'web-01' })
  })
})
