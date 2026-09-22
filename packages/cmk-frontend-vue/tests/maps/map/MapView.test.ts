/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import type { SignedMap } from '@/maps/api/mapConfig'
import MapViewComponent from '@/maps/map/MapView.vue'
import type { MapConfig, MapRead, MapView } from '@/maps/types/api'

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

// The per-type renderers are the observable output of the dispatch under test:
// each gets a recognisable stub so a test can assert exactly one is mounted. The
// overlay/modal children are irrelevant to dispatch and auto-stubbed away.
const rendererStub = (testid: string) => ({ template: `<div data-testid="${testid}" />` })
const stubs = {
  // Keyed by the tag the view uses: the per-type views are async components, so
  // there is no component name to stub them by.
  'world-map-view': rendererStub('renderer-worldmap'),
  'flow-map-view': rendererStub('renderer-flow'),
  MapCanvas: rendererStub('renderer-static'),
  MapSearch: true,
  ProblemsOnlyToggle: true,
  DetailDrawer: true,
  MapsLink: true,
  CmkLoading: true,
  CmkButton: true,
  teleport: true
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

const allRendererTestIds = ['renderer-worldmap', 'renderer-flow', 'renderer-static']

// Assert the named renderer is the only one on screen.
async function expectOnlyRenderer(testid: string) {
  await waitFor(() => expect(screen.getByTestId(testid)).toBeInTheDocument())
  for (const other of allRendererTestIds) {
    if (other !== testid) {
      expect(screen.queryByTestId(other)).toBeNull()
    }
  }
}

// The static map is the one view this file lets render for real: the others are
// stubbed at their tag, but the error placeholder and the "map not found" state
// come from inside ``StaticMapView``. Its chunk is loaded up front so the
// dynamic import is not on the clock of every ``waitFor`` below.
beforeAll(async () => {
  await import('@/maps/map/static/StaticMapView.vue')
})

describe('MapView – map-type dispatch', () => {
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

  it('renders the static MapCanvas for a static view', async () => {
    opensMap(newMapView('static'))
    renderMap()
    await expectOnlyRenderer('renderer-static')
  })

  it('renders the WorldMapView for a worldmap view', async () => {
    opensMap(newMapView('worldmap'))
    renderMap()
    await expectOnlyRenderer('renderer-worldmap')
  })

  it('renders the FlowMapView for a flow view', async () => {
    opensMap(newMapView('flow'))
    renderMap()
    await expectOnlyRenderer('renderer-flow')
  })

  // The remaining map types draw themselves, and each arrives with its own
  // commit; until then the map area says so rather than drawing them wrong.
  it.each(['radar', 'foldertree', 'presentation'])(
    'stands in for a %s view it cannot draw yet',
    async (mapType) => {
      opensMap(newMapView(mapType))
      renderMap()
      await waitFor(() =>
        expect(screen.getByText('This map type cannot be shown yet')).toBeInTheDocument()
      )
      for (const testid of allRendererTestIds) {
        expect(screen.queryByTestId(testid)).toBeNull()
      }
    }
  )

  it('dispatches on the view type alone, connection or not', async () => {
    // What a flow map without a connection says is its own view's business.
    opensMap(newMapView('flow'), { connection_id: '' })
    renderMap()
    await expectOnlyRenderer('renderer-flow')
  })
})

describe('MapView – loading / error / read-only states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    services = fakeMapsServices()
    vi.stubGlobal('EventSource', FakeEventSource)
    services.nav.replace({ view: 'map', name: 'map1' })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the loading spinner and no renderer while the map fetch is in flight', async () => {
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

describe('MapView – what the settings slide-in is handed', () => {
  // Ownership and sharing live on the map-list row, not in the daemon config
  // the canvas renders from. A settings form built from the config alone reads
  // as private and saves that back, so renaming a map shared with everyone
  // would quietly unpublish it -- and its Delete button would never appear.
  let handedMap: MapRead | null

  const openSettingsTopbar = defineComponent({
    emits: ['open-settings'],
    setup(_props, { emit }) {
      return () => h('button', { onClick: () => emit('open-settings') }, 'Map settings')
    }
  })

  const settingsProbe = defineComponent({
    props: { map: { type: Object, required: true } },
    setup(props) {
      handedMap = props.map as MapRead
      return () => h('div', { 'data-testid': 'settings-open' })
    }
  })

  beforeEach(() => {
    vi.clearAllMocks()
    handedMap = null
    services = fakeMapsServices()
    vi.stubGlobal('EventSource', FakeEventSource)
    services.nav.replace({ view: 'map', name: 'map1' })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('carries the sharing and delete rights over from the map list', async () => {
    opensMap(newMapView('static'))
    services.maps.maps.value = [
      {
        name: 'map1',
        alias: 'Map 1',
        owner: 'cmkadmin',
        public: true,
        can_edit: true,
        can_delete: true
      }
    ] as typeof services.maps.maps.value

    const { global: provided } = provideServices(services)
    render(MapViewComponent, {
      global: {
        ...provided,
        stubs: { ...stubs, MapViewTopbar: openSettingsTopbar, MapSettingsModal: settingsProbe }
      }
    })

    await waitFor(() => expect(screen.getByTestId('renderer-static')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Map settings' }))

    await waitFor(() => expect(screen.getByTestId('settings-open')).toBeInTheDocument())
    expect(handedMap).toMatchObject({
      alias: 'Map 1',
      owner: 'cmkadmin',
      public: true,
      can_delete: true
    })
  })
})
