/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, delay, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MapConfigApi } from '@/maps/api/mapConfig'
import { MapStatesApi } from '@/maps/api/mapStates'
import { createMapsDaemonClient } from '@/maps/api/transport'
import { MapService } from '@/maps/services/MapService'
import type { MapConfig, MapRead } from '@/maps/types/api'

import { aMap, anObject, newMapView } from '../support/fixtures'

// Map config CRUD goes through the official Checkmk REST API (openapi-fetch,
// rooted at /api/internal). The tests simulate that boundary with msw, so the
// REAL api client runs — URL building, the domain-object→MapRead mapping and
// the signed-map decode are exercised for free.

const sampleConfig: MapConfig = aMap({
  name: 'map1',
  alias: 'Map 1',
  icon_size: 30,
  connection_id: 'live_1',
  rotation_interval: 0,
  sort_order: 0,
  click_action: 'link',
  view: newMapView('static'),
  objects: []
})

// The one list row, in the SPA's ``MapRead`` shape the store expects after the
// client flattens the REST domain-object collection below.
const sampleMaps: MapRead[] = [
  {
    name: 'map1',
    alias: 'Map 1',
    connection_id: 'live_1',
    view_type: 'static',
    view: newMapView('static'),
    object_count: 0,
    icon_size: 30,
    rotation_interval: 0,
    sort_order: 0,
    version: 0,
    hide_in_monitor_menu: false,
    render_mode: 'default',
    background_image: null,
    background_color: null,
    click_action: 'link',
    hover_template: null,
    context_template: null,
    default_z: 1,
    can_edit: true,
    can_delete: true,
    owner: 'alice',
    is_builtin: false,
    public: false
  }
]

// The REST list domain-object the client maps into ``sampleMaps``.
const listResponse = {
  id: 'map',
  domainType: 'map',
  value: [
    {
      domainType: 'map',
      id: 'map1',
      title: 'Map 1',
      extensions: {
        owner: 'alice',
        visibility: { publish: 'private', hide_in_monitor_menu: false },
        is_builtin: false,
        can_edit: true,
        can_delete: true,
        summary: {
          name: 'map1',
          alias: 'Map 1',
          connection_id: 'live_1',
          view_type: 'static',
          view: newMapView('static'),
          click_action: 'link',
          object_count: 0,
          icon_size: 30,
          rotation_interval: 0,
          sort_order: 0
        }
      },
      links: []
    }
  ],
  links: []
}

// getMapFromGui returns the GUI-signed bundle; the store renders from ``config``
// (which the real client decodes from the signed base64url bytes) and keeps
// ``config_b64``/``sig`` for the daemon register.
const sampleConfigB64 = btoa(JSON.stringify(sampleConfig))
  .replace(/\+/g, '-')
  .replace(/\//g, '_')
  .replace(/=+$/, '')
// The REST show/create/update domain-object the client decodes / returns.
const mapObjectResponse = {
  domainType: 'map',
  id: 'map1',
  title: 'Map 1',
  extensions: {
    owner: '',
    visibility: { publish: 'private', hide_in_monitor_menu: false },
    is_builtin: false,
    can_edit: true,
    can_delete: true,
    config: sampleConfig,
    config_b64: sampleConfigB64,
    sig: 'cw'
  },
  links: []
}

// Per-test request log, so the assertions about avoided round-trips
// ("no extra list() fetch") keep working at the network boundary.
let listCalls: number
let getCalls: string[]
let saveRequests: { config: MapConfig; visibility?: unknown }[]
let deletedNames: string[]

const server = useMswServer(
  http.get('*/api/internal/domain-types/map/collections/all', () => {
    listCalls += 1
    return HttpResponse.json(listResponse)
  }),
  http.get('*/api/internal/objects/map/:name', ({ params }) => {
    getCalls.push(String(params['name']))
    return HttpResponse.json(mapObjectResponse)
  }),
  http.post('*/api/internal/domain-types/map/collections/all', async ({ request }) => {
    saveRequests.push(JSON.parse(await request.text()))
    return HttpResponse.json(mapObjectResponse)
  }),
  http.put('*/api/internal/objects/map/:name', async ({ request }) => {
    saveRequests.push(JSON.parse(await request.text()))
    return HttpResponse.json(mapObjectResponse)
  }),
  http.delete('*/api/internal/objects/map/:name', ({ params }) => {
    deletedNames.push(String(params['name']))
    return new HttpResponse(null, { status: 204 })
  })
)

beforeEach(() => {
  listCalls = 0
  getCalls = []
  saveRequests = []
  deletedNames = []
})

function newService(): MapService {
  return new MapService(
    new MapConfigApi(),
    new MapStatesApi(createMapsDaemonClient({ headers: () => undefined }))
  )
}

describe('MapService', () => {
  it('starts with empty maps', () => {
    const store = newService()
    expect(store.maps.value).toEqual([])
    expect(store.loading.value).toBe(false)
    expect(store.error.value).toBeNull()
  })

  it('fetchMaps() populates maps on success', async () => {
    const store = newService()
    await store.fetchMaps()
    expect(store.maps.value).toEqual(sampleMaps)
    expect(store.loading.value).toBe(false)
    expect(store.error.value).toBeNull()
  })

  it('fetchMaps() sets error on failure', async () => {
    server.use(
      http.get('*/api/internal/domain-types/map/collections/all', () =>
        HttpResponse.json({ title: 'Error', detail: 'Network error' }, { status: 500 })
      )
    )
    const store = newService()
    await store.fetchMaps()
    expect(store.error.value).toContain('Network error')
    expect(store.loading.value).toBe(false)
    expect(store.maps.value).toEqual([])
  })

  it('fetchMap() clears currentMap immediately', async () => {
    const store = newService()
    store.currentMap.value = sampleConfig

    const fetchPromise = store.fetchMap('map1')
    expect(store.currentMap.value).toBeNull()
    await fetchPromise
    expect(store.currentMap.value).toEqual(sampleConfig)
    expect(store.currentMapSig.value).toEqual({ config_b64: sampleConfigB64, sig: 'cw' })
  })

  it('fetchMap() sets error on failure', async () => {
    server.use(
      http.get('*/api/internal/objects/map/:name', () =>
        HttpResponse.json({ title: 'Not Found', detail: 'Not found' }, { status: 404 })
      )
    )
    const store = newService()
    await store.fetchMap('nonexistent')
    expect(store.error.value).toContain('Not found')
    expect(store.currentMap.value).toBeNull()
  })

  it('flushSave() persists the map captured when the save was scheduled, not the one now open', async () => {
    const store = newService()
    await store.fetchMap('map1')
    // Edit map1 in place and arm the debounce, as the editor does.
    store.currentMap.value!.alias = 'edited'
    store.scheduleSave()
    // Switch to another map within the debounce window (what fetchMap does).
    store.currentMap.value = { ...sampleConfig, name: 'map2', alias: 'Map 2' }
    await store.flushSave()
    // The edit is persisted against map1, never the freshly-opened map2.
    expect(saveRequests).toHaveLength(1)
    expect(saveRequests[0]!.config.name).toBe('map1')
    expect(saveRequests[0]!.config.alias).toBe('edited')
  })

  it('cloneMap() keeps the clone out of the Monitor menu where its source is', async () => {
    const store = newService()
    await store.fetchMaps()
    store.maps.value[0]!.hide_in_monitor_menu = true

    await store.cloneMap('map1', 'map1_copy')

    expect(saveRequests).toHaveLength(1)
    expect(saveRequests[0]!.config.name).toBe('map1_copy')
    expect(saveRequests[0]!.visibility).toEqual({ publish: 'private', hide_in_monitor_menu: true })
  })

  it('fetchMap() staleness guard: a slower earlier load never overwrites a newer map', async () => {
    const store = newService()
    server.use(
      http.get('*/api/internal/objects/map/:name', async ({ params }) => {
        const name = String(params['name'])
        if (name === 'slow') {
          await delay(50)
        }
        const cfg: MapConfig = aMap({ ...sampleConfig, name })
        const b64 = btoa(JSON.stringify(cfg))
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/, '')
        return HttpResponse.json({
          ...mapObjectResponse,
          id: name,
          extensions: { ...mapObjectResponse.extensions, config: cfg, config_b64: b64 }
        })
      })
    )
    // Start the slow map first, then a fast one — the fast load resolves first
    // and wins; the slow load must not clobber it when it resolves late.
    const slow = store.fetchMap('slow')
    const fast = store.fetchMap('fast')
    await Promise.all([slow, fast])
    expect(store.currentMap.value?.name).toBe('fast')
    expect(store.loading.value).toBe(false)
  })

  it('fetchMap() stamps the resolved titles onto the map links', async () => {
    const store = newService()
    const cfg: MapConfig = aMap({
      ...sampleConfig,
      objects: [
        anObject({ id: 'link-1', type: 'map', map_name: 'dc-2' }),
        anObject({ id: 'link-2', type: 'map', map_name: 'private-map' }),
        anObject({ id: 'host-1', type: 'host', host_name: 'db01' })
      ]
    })
    server.use(
      http.get('*/api/internal/objects/map/:name', () =>
        HttpResponse.json({
          ...mapObjectResponse,
          extensions: {
            ...mapObjectResponse.extensions,
            config: cfg,
            config_b64: btoa(JSON.stringify(cfg))
              .replace(/\+/g, '-')
              .replace(/\//g, '_')
              .replace(/=+$/, ''),
            // ``private-map`` is one the requesting user may not see, so the
            // server left it out.
            map_link_titles: { 'dc-2': 'Datacenter 2' }
          }
        })
      )
    )

    await store.fetchMap('map1')

    const objects = store.currentMap.value!.objects
    expect(objects[0]!.map_title).toBe('Datacenter 2')
    expect(objects[1]!.map_title).toBeNull()
    expect(objects[2]).not.toHaveProperty('map_title')
  })

  it('createMap() persists via the REST API and appends in place', async () => {
    const store = newService()
    const result = await store.createMap('map1', 'Map 1')
    expect(saveRequests).toHaveLength(1)
    expect(saveRequests[0]!.config.name).toBe('map1')
    // In-place append: no extra list() round-trip.
    expect(listCalls).toBe(0)
    expect(store.maps.value).toHaveLength(1)
    expect(store.maps.value[0]!.name).toBe('map1')
    expect(result.name).toBe('map1')
  })

  it('deleteMap() removes the map in place without re-fetching', async () => {
    const store = newService()
    await store.fetchMaps()
    expect(listCalls).toBe(1)

    await store.deleteMap('map1')
    // The server resolves the exact instance by name (own/foreign/built-in).
    expect(deletedNames).toEqual(['map1'])
    // No extra list() round-trip — map is removed in place.
    expect(listCalls).toBe(1)
    expect(store.maps.value).toEqual([])
  })
})

describe('MapService.loadAutoObjects()', () => {
  function serviceWithAutoObjects(...batches: MapConfig['objects'][]): MapService {
    const fetchAutoObjects = vi.fn()
    for (const batch of batches) {
      fetchAutoObjects.mockResolvedValueOnce(batch)
    }
    return new MapService(new MapConfigApi(), { fetchAutoObjects })
  }

  const world = (): MapConfig =>
    aMap({
      name: 'world',
      view: {
        type: 'worldmap',
        lat: 51,
        lng: 10,
        zoom: 5,
        auto_source: 'all_hosts',
        auto_filter_value: '',
        problems_only: false
      },
      objects: [anObject({ id: 'core', type: 'host' })]
    })

  it('replaces the hosts of an earlier load and keeps the rest', async () => {
    const store = serviceWithAutoObjects(
      [anObject({ id: 'auto:db01', type: 'host' })],
      [anObject({ id: 'auto:db02', type: 'host' })]
    )
    store.currentMap.value = world()

    await store.loadAutoObjects('world', true)
    store.currentMap.value!.objects.push(anObject({ id: 'placed', type: 'host' }))
    await store.loadAutoObjects('world', true)

    expect(store.currentMap.value!.objects.map((object) => object.id)).toEqual([
      'core',
      'placed',
      'auto:db02'
    ])
  })

  it('stops waiting for the hosts once they are in', async () => {
    const store = serviceWithAutoObjects([])
    store.currentMap.value = world()
    store.autoObjects.value = 'loading'

    await store.loadAutoObjects('world', true)

    expect(store.autoObjects.value).toBe('loaded')
  })

  it('does not take a failed load for an answer', async () => {
    const store = new MapService(new MapConfigApi(), {
      fetchAutoObjects: vi.fn().mockRejectedValue(new Error('HTTP 500'))
    })
    store.currentMap.value = world()
    store.autoObjects.value = 'loading'

    await expect(store.loadAutoObjects('world', true)).rejects.toThrow()

    expect(store.autoObjects.value).toBe('failed')
  })

  it('stops waiting for the hosts of a map the daemon was never handed', async () => {
    const fetchAutoObjects = vi.fn()
    const store = new MapService(new MapConfigApi(), { fetchAutoObjects })
    store.currentMap.value = world()
    store.autoObjects.value = 'loading'

    await store.loadAutoObjects('world', false)

    expect(store.autoObjects.value).toBe('failed')
    expect(fetchAutoObjects).not.toHaveBeenCalled()
  })

  it('drops the hosts of an auto source that was removed', async () => {
    const store = serviceWithAutoObjects([anObject({ id: 'auto:db01', type: 'host' })])
    store.currentMap.value = world()
    await store.loadAutoObjects('world', true)

    store.currentMap.value = { ...store.currentMap.value!, view: aMap().view }
    await store.loadAutoObjects('world', true)

    expect(store.currentMap.value.objects.map((object) => object.id)).toEqual(['core'])
    expect(store.autoObjects.value).toBe('none')
  })

  it('leaves a map that was switched to meanwhile alone', async () => {
    const store = serviceWithAutoObjects([anObject({ id: 'auto:db01', type: 'host' })])
    store.currentMap.value = world()

    const loading = store.loadAutoObjects('world', true)
    store.currentMap.value = aMap({ name: 'other', objects: [] })
    await loading

    expect(store.currentMap.value!.objects).toEqual([])
  })
})
