/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, delay, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, watchEffect } from 'vue'

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
    rotation_pools: [],
    sort_order: 0,
    version: 0,
    hide_in_monitor_menu: false,
    render_mode: 'default',
    background_image: null,
    background_color: null,
    background_style: 'single',
    background_position: 'top_left',
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

const shown = { headers: { ETag: '"shown"' } }

const signedMapResponse = {
  owner: '',
  visibility: { publish: 'private', hide_in_monitor_menu: false },
  is_builtin: false,
  can_edit: true,
  can_delete: true,
  config_b64: sampleConfigB64,
  sig: 'cw',
  map_link_titles: {}
}

// Per-test request log, so the assertions about avoided round-trips
// ("no extra list() fetch") keep working at the network boundary.
let listCalls: number
let getCalls: string[]
let saveRequests: { config: MapConfig; visibility?: unknown }[]
let ifMatches: (string | null)[]
let deletedNames: string[]

const server = useMswServer(
  http.get('*/api/internal/domain-types/map/collections/all', () => {
    listCalls += 1
    return HttpResponse.json(listResponse)
  }),
  http.get('*/api/internal/objects/maps_signed_map/:name', ({ params }) => {
    getCalls.push(String(params['name']))
    return HttpResponse.json(signedMapResponse, shown)
  }),
  http.post('*/api/internal/domain-types/map/collections/all', async ({ request }) => {
    saveRequests.push(JSON.parse(await request.text()))
    return HttpResponse.json(mapObjectResponse)
  }),
  http.put('*/api/internal/objects/map/:name', async ({ request }) => {
    ifMatches.push(request.headers.get('If-Match'))
    saveRequests.push(JSON.parse(await request.text()))
    return HttpResponse.json(mapObjectResponse, {
      headers: { ETag: `"saved-${saveRequests.length}"` }
    })
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
  ifMatches = []
  deletedNames = []
})

const saveConflict = http.put('*/api/internal/objects/map/:name', () =>
  HttpResponse.json({ title: 'Precondition failed', detail: "ETag didn't match." }, { status: 412 })
)

function newService(): MapService {
  return new MapService(new MapConfigApi(), new MapStatesApi(createMapsDaemonClient()))
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

  it("fetches the list for another view without touching the shown map's error", async () => {
    const store = newService()
    store.error.value = 'Map vanished'
    expect(await store.ensureMaps()).toEqual(sampleMaps)
    await store.ensureMaps()
    expect(listCalls).toBe(1)
    expect(store.error.value).toBe('Map vanished')
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

    const onSigned = vi.fn()
    const fetchPromise = store.fetchMap('map1', onSigned)
    expect(store.currentMap.value).toBeNull()
    await fetchPromise
    expect(store.currentMap.value).toEqual(sampleConfig)
    expect(onSigned).toHaveBeenCalledWith({ config_b64: sampleConfigB64, sig: 'cw' })
  })

  it('fetchMap() sets error on failure', async () => {
    server.use(
      http.get('*/api/internal/objects/maps_signed_map/:name', () =>
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

  it('flushSave() hands a refused save back quietly and keeps the map open', async () => {
    server.use(
      http.put('*/api/internal/objects/map/:name', () =>
        HttpResponse.json(
          { title: 'Invalid Livestatus filter', detail: "Object 'g': unknown column 'nme'" },
          { status: 400 }
        )
      )
    )
    const store = newService()
    await store.fetchMap('map1')
    store.scheduleSave()

    const failure = await store.flushSave({ quiet: true })

    expect(failure).toBeInstanceOf(Error)
    expect(store.saveError.value).toBeNull()
    expect(store.error.value).toBeNull()
    expect(store.currentMap.value?.name).toBe('map1')
  })

  it('a refused save in the background says why, not what the map failed to load', async () => {
    server.use(
      http.put('*/api/internal/objects/map/:name', () =>
        HttpResponse.json(
          { title: 'Invalid Livestatus filter', detail: "Object 'g': unknown column 'nme'" },
          { status: 400 }
        )
      )
    )
    const store = newService()
    await store.fetchMap('map1')
    store.scheduleSave()

    await vi.waitFor(() => expect(store.saveError.value).not.toBeNull(), { timeout: 2000 })

    expect(store.saveError.value).toEqual({ text: "Object 'g': unknown column 'nme'" })
    expect(store.error.value).toBeNull()
  })

  it('shows the stored map again after a save in the background was refused', async () => {
    server.use(
      http.put('*/api/internal/objects/map/:name', () =>
        HttpResponse.json({ title: 'Bad Request', detail: 'refused' }, { status: 400 })
      )
    )
    const store = newService()
    await store.fetchMap('map1')
    store.currentMap.value!.alias = 'refused'
    store.scheduleSave()

    await vi.waitFor(() => expect(store.currentMap.value?.alias).toBe('Map 1'), { timeout: 2000 })
  })

  it('hands the stored map to its listeners after a save in the background was refused', async () => {
    server.use(
      http.put('*/api/internal/objects/map/:name', () =>
        HttpResponse.json({ title: 'Bad Request', detail: 'refused' }, { status: 400 })
      )
    )
    const store = newService()
    const onSaved = vi.fn()
    store.onSaved(onSaved)
    await store.fetchMap('map1')
    store.currentMap.value!.alias = 'refused'
    store.scheduleSave()

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled(), { timeout: 2000 })

    expect(onSaved).toHaveBeenCalledWith('map1', expect.objectContaining({ sig: 'cw' }), true)
  })

  it('keeps the edit of a save in the background that did not get through', async () => {
    server.use(
      http.put('*/api/internal/objects/map/:name', () =>
        HttpResponse.json({ title: 'Service Unavailable', detail: 'restarting' }, { status: 503 })
      )
    )
    const store = newService()
    await store.fetchMap('map1')
    store.currentMap.value!.alias = 'kept'
    store.scheduleSave()

    await vi.waitFor(() => expect(store.saveError.value).not.toBeNull(), { timeout: 2000 })

    expect(getCalls).toEqual(['map1'])
    expect(store.currentMap.value?.alias).toBe('kept')
  })

  it('saves each version on the one the save before stored', async () => {
    const store = newService()
    await store.fetchMap('map1')

    store.scheduleSave()
    const first = store.flushSave()
    store.scheduleSave()
    await Promise.all([first, store.flushSave()])

    expect(ifMatches).toEqual(['"shown"', '"saved-1"'])
  })

  describe('a save someone else saved before', () => {
    async function conflicted(): Promise<MapService> {
      const store = newService()
      await store.fetchMap('map1')
      server.use(saveConflict)
      store.currentMap.value!.alias = 'mine'
      store.scheduleSave()
      await store.flushSave()
      server.resetHandlers()
      return store
    }

    it('leaves an effect that opened the map alone', async () => {
      const store = newService()
      let opened = 0
      const stop = watchEffect(() => {
        opened += 1
        void store.fetchMap('map1')
      })
      await vi.waitFor(() => expect(store.currentMap.value).not.toBeNull())
      server.use(saveConflict)
      store.scheduleSave()
      await store.flushSave()
      await nextTick()
      stop()

      expect(opened).toBe(1)
      expect(store.saveConflict.value?.name).toBe('map1')
    })

    it('keeps the edits unsaved until the operator chooses', async () => {
      const store = await conflicted()

      store.scheduleSave()
      await new Promise((resolve) => setTimeout(resolve, 500))

      expect(store.saveConflict.value?.name).toBe('map1')
      expect(store.saveError.value).toBeNull()
      expect(store.currentMap.value?.alias).toBe('mine')
      expect(ifMatches).toEqual([])
    })

    it('shows the other save on a reload', async () => {
      const store = await conflicted()

      await store.reloadOnConflict()

      expect(store.saveConflict.value).toBeNull()
      expect(store.currentMap.value?.alias).toBe('Map 1')
      expect(ifMatches).toEqual([])
    })

    it('stores the edits over the other save on an overwrite', async () => {
      const store = await conflicted()

      await store.overwriteOnConflict()

      expect(store.saveConflict.value).toBeNull()
      expect(ifMatches).toEqual(['*'])
      expect(saveRequests.at(-1)!.config.alias).toBe('mine')
    })
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
      http.get('*/api/internal/objects/maps_signed_map/:name', async ({ params }) => {
        const name = String(params['name'])
        if (name === 'slow') {
          await delay(50)
        }
        const cfg: MapConfig = aMap({ ...sampleConfig, name })
        const b64 = btoa(JSON.stringify(cfg))
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/, '')
        return HttpResponse.json({ ...signedMapResponse, config_b64: b64 }, shown)
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
      http.get('*/api/internal/objects/maps_signed_map/:name', () =>
        HttpResponse.json(
          {
            ...signedMapResponse,
            config_b64: btoa(JSON.stringify(cfg))
              .replace(/\+/g, '-')
              .replace(/\//g, '_')
              .replace(/=+$/, ''),
            // ``private-map`` is one the requesting user may not see, so the
            // server left it out.
            map_link_titles: { 'dc-2': 'Datacenter 2' }
          },
          shown
        )
      )
    )

    await store.fetchMap('map1')

    const objects = store.currentMap.value!.objects
    expect(objects[0]!.map_title).toBe('Datacenter 2')
    expect(objects[1]!.map_title).toBeNull()
    expect(objects[2]).not.toHaveProperty('map_title')
  })

  it('fetchMap() takes over a prefetched map instead of loading it again', async () => {
    const store = newService()

    store.prefetch('map1')
    await store.fetchMap('map1')

    expect(getCalls).toEqual(['map1'])
    expect(store.currentMap.value).toEqual(sampleConfig)
  })

  it('fetchMap() loads a map other than the prefetched one itself', async () => {
    const store = newService()

    store.prefetch('other')
    await store.fetchMap('map1')

    expect(getCalls).toEqual(['other', 'map1'])
    expect(store.currentMap.value).toEqual(sampleConfig)
  })

  it('fetchMap() loads a map again whose prefetch failed', async () => {
    const store = newService()
    let failFirst = true
    server.use(
      http.get('*/api/internal/objects/maps_signed_map/:name', ({ params }) => {
        getCalls.push(String(params['name']))
        if (failFirst) {
          failFirst = false
          return HttpResponse.json({ title: 'Unavailable' }, { status: 503 })
        }
        return HttpResponse.json(signedMapResponse, shown)
      })
    )

    store.prefetch('map1')
    await vi.waitFor(() => expect(getCalls).toEqual(['map1']))
    await new Promise((resolve) => setTimeout(resolve, 0))
    await store.fetchMap('map1')

    expect(getCalls).toEqual(['map1', 'map1'])
    expect(store.currentMap.value).toEqual(sampleConfig)
  })

  it('fetchMap() hands out the signature before the map is rendered', async () => {
    const store = newService()
    let renderedWhenSigned: MapConfig | null | undefined

    await store.fetchMap('map1', () => {
      renderedWhenSigned = store.currentMap.value
    })

    expect(renderedWhenSigned).toBeNull()
    expect(store.currentMap.value).toEqual(sampleConfig)
  })

  it('flushSave() tells its listeners the signed bytes of the saved map', async () => {
    const store = newService()
    const listener = vi.fn()
    store.onSaved(listener)
    await store.fetchMap('map1')
    store.scheduleSave()

    await store.flushSave()

    expect(listener).toHaveBeenCalledWith('map1', { config_b64: sampleConfigB64, sig: 'cw' }, false)
  })

  describe('showSaved()', () => {
    // Math.random is pinned to 0, so a view loads exactly this long after a save.
    const delay = 2000

    beforeEach(() => {
      vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
      vi.spyOn(Math, 'random').mockReturnValue(0)
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    function serveSavedVersion(sig: string): void {
      server.use(
        http.get('*/api/internal/objects/maps_signed_map/:name', ({ params }) => {
          getCalls.push(String(params['name']))
          return HttpResponse.json({ ...signedMapResponse, sig }, shown)
        })
      )
    }

    it('loads the open map again for another saved version', async () => {
      const store = newService()
      await store.fetchMap('map1')
      store.currentMap.value!.alias = 'outdated'
      serveSavedVersion('newer')

      store.showSaved('map1', 'newer')
      await vi.advanceTimersByTimeAsync(delay)

      await vi.waitFor(() => expect(store.currentMap.value).toEqual(sampleConfig))
      expect(getCalls).toEqual(['map1', 'map1'])
    })

    it('loads several saves in a row once, also while the editing goes on', async () => {
      const store = newService()
      await store.fetchMap('map1')
      serveSavedVersion('second')

      store.showSaved('map1', 'first')
      await vi.advanceTimersByTimeAsync(delay / 2)
      store.showSaved('map1', 'second')
      expect(getCalls).toEqual(['map1'])
      await vi.advanceTimersByTimeAsync(delay / 2)

      await vi.waitFor(() => expect(store.currentMap.value).toEqual(sampleConfig))
      expect(getCalls).toEqual(['map1', 'map1'])
    })

    it('keeps the version the map shows already', async () => {
      const store = newService()
      await store.fetchMap('map1')

      store.showSaved('map1', 'cw')
      await vi.advanceTimersByTimeAsync(delay)

      expect(getCalls).toEqual(['map1'])
    })

    it('keeps edits not saved yet', async () => {
      const store = newService()
      await store.fetchMap('map1')

      store.showSaved('map1', 'newer')
      await vi.advanceTimersByTimeAsync(delay - 100)
      store.scheduleSave()
      await vi.advanceTimersByTimeAsync(100)

      expect(getCalls).toEqual(['map1'])
      await store.flushSave()
    })

    it('loads nothing once the view stops following saves', async () => {
      const store = newService()
      await store.fetchMap('map1')

      store.showSaved('map1', 'newer')
      store.cancelShowSaved()
      await vi.advanceTimersByTimeAsync(delay)

      expect(getCalls).toEqual(['map1'])
    })
  })

  it('saveMapMetadata() shows the sharing the server stored, not the one asked for', async () => {
    const store = newService()
    await store.fetchMap('map1')

    // The server narrowed the requested scope; the save response is private.
    await store.saveMapMetadata('map1', {}, { public: true, hide_in_monitor_menu: true })

    expect(store.currentMapAccess.value).toMatchObject({
      public: false,
      hide_in_monitor_menu: false
    })
  })

  it('saveMapMetadata() on a map that is not open leaves nothing to save', async () => {
    const store = newService()

    await store.saveMapMetadata('map1', { alias: 'renamed' })
    await store.flushSave()

    expect(saveRequests).toHaveLength(1)
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
