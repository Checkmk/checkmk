/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SignedMap } from '@/maps/api/mapConfig'
import MapViewComponent from '@/maps/map/MapView.vue'
import type { MapConfig, MapView } from '@/maps/types/api'

import { aMap, newMapView } from '../support/fixtures'
import { fakeMapsServices, provideServices } from '../support/services'

// connectToMap opens an EventSource; jsdom has none. A minimal stand-in keeps the
// SSE path from throwing without driving any events (this suite tests dispatch,
// not the live stream).
class FakeEventSource {
  static readonly OPEN = 1
  onopen: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  readyState = 0
  constructor(public url: string) {}
  close() {
    this.readyState = 2
  }
}

// The canvas is the observable output of the dispatch under test: a recognisable
// stub says whether the map got drawn. The chrome around it is irrelevant here
// and auto-stubbed away.
const stubs = {
  MapCanvas: { template: `<div data-testid="renderer-static" />` },
  MapSearch: true,
  ProblemsOnlyToggle: true,
  DetailDrawer: true,
  MapsLink: true,
  CmkLoading: true
}

function signedMap(view: MapView, extra: Partial<MapConfig> = {}): SignedMap {
  const config: MapConfig = aMap({
    name: 'map1',
    alias: 'Map 1',
    icon_size: 30,
    connection_id: 'live_1',
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    view,
    objects: [],
    ...extra
  })
  return { config, config_b64: 'cfg', sig: 'sig', owner: '', map_link_titles: {} }
}

let services: ReturnType<typeof fakeMapsServices>

function opensMap(view: MapView, extra: Partial<MapConfig> = {}): void {
  vi.mocked(services.apis.mapConfig.get).mockResolvedValue(signedMap(view, extra))
}

function renderMap() {
  const { global: provided } = provideServices(services)
  return render(MapViewComponent, {
    global: { ...provided, stubs }
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  services = fakeMapsServices()
  vi.stubGlobal('EventSource', FakeEventSource)
  // Point navigation at a map so the shell fetches and renders one.
  services.nav.replace({ view: 'map', name: 'map1' })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('MapView – map-type dispatch', () => {
  it('draws the canvas for a static view', async () => {
    opensMap(newMapView('static'))
    renderMap()
    await waitFor(() => expect(screen.getByTestId('renderer-static')).toBeInTheDocument())
  })

  // The other map types draw themselves, and each arrives with its own commit;
  // until then the map area says so rather than rendering a worldmap as a
  // static one.
  it.each(['worldmap', 'radar', 'foldertree', 'flow', 'presentation'])(
    'stands in for a %s view it cannot draw yet',
    async (mapType) => {
      opensMap(newMapView(mapType))
      renderMap()
      await waitFor(() =>
        expect(screen.getByText('This map type cannot be shown yet')).toBeInTheDocument()
      )
      expect(screen.queryByTestId('renderer-static')).toBeNull()
    }
  )
})

describe('MapView – loading / error / read-only states', () => {
  it('shows the loading spinner and no canvas while the map fetch is in flight', async () => {
    // A fetch that never settles keeps the store's loading flag set.
    vi.mocked(services.apis.mapConfig.get).mockReturnValue(new Promise<SignedMap>(() => {}))
    renderMap()
    await waitFor(() => expect(screen.getByText('Loading map…')).toBeInTheDocument())
    expect(screen.queryByTestId('renderer-static')).toBeNull()
  })

  it('surfaces the store error and renders no map when the fetch fails', async () => {
    vi.mocked(services.apis.mapConfig.get).mockRejectedValue(new Error('Map vanished'))
    renderMap()
    await waitFor(() => expect(screen.getByText('Map vanished')).toBeInTheDocument())
    expect(screen.queryByTestId('renderer-static')).toBeNull()
    expect(screen.queryByText('Loading map…')).toBeNull()
  })

  it('shows the Read-only badge for a read-only map', async () => {
    opensMap(newMapView('static'), { readonly: true })
    renderMap()
    await waitFor(() => expect(screen.getByTestId('renderer-static')).toBeInTheDocument())
    expect(screen.getByText('Read-only')).toBeInTheDocument()
  })

  it('omits the Read-only badge for an editable map', async () => {
    opensMap(newMapView('static'), { readonly: false })
    renderMap()
    await waitFor(() => expect(screen.getByTestId('renderer-static')).toBeInTheDocument())
    expect(screen.queryByText('Read-only')).toBeNull()
  })
})

describe('MapView – breadcrumb', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    services = fakeMapsServices()
    vi.stubGlobal('EventSource', FakeEventSource)
    services.nav.replace({ view: 'map', name: 'map1' })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('links back to the map list and ends on the open map', async () => {
    opensMap(newMapView('static'))
    renderMap()
    await waitFor(() => expect(screen.getByTestId('renderer-static')).toBeInTheDocument())
    expect(screen.getByRole('link', { name: 'Maps' })).toHaveAttribute(
      'href',
      services.nav.href({ view: 'home' })
    )
    expect(screen.queryByRole('link', { name: 'Map 1' })).toBeNull()
  })
})
