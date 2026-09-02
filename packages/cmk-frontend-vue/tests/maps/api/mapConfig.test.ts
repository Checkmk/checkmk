/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { MapConfigApi } from '@/maps/api/mapConfig'
import type { MapConfig } from '@/maps/types/api'

import { aMap, newMapView } from '../support/fixtures'
import { type SeenRequest, snapshot, useMswServer } from '../support/http'

vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
  const { interceptableRestClient } = await import('../support/http')
  return interceptableRestClient(await importOriginal<Record<string, unknown>>())
})

const api = new MapConfigApi()

const server = useMswServer()

describe('api client — map CRUD via the Checkmk REST API', () => {
  function base64url(value: object): string {
    return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  }

  const staticMap: MapConfig = aMap({
    name: 'map1',
    alias: 'Map One',
    connection_id: 'live_1',
    icon_size: null,
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    view: newMapView('static'),
    objects: []
  })

  it('lists maps and flattens the domain collection into MapRead rows', async () => {
    server.use(
      http.get('*/api/internal/domain-types/map/collections/all', () =>
        HttpResponse.json({
          id: 'map',
          domainType: 'map',
          value: [
            {
              domainType: 'map',
              id: 'map1',
              title: 'Map One',
              extensions: {
                owner: 'alice',
                visibility: { publish: 'contact_groups', groups: ['ops'] },
                is_builtin: false,
                can_edit: true,
                can_delete: false,
                summary: {
                  name: 'map1',
                  alias: 'Map One',
                  connection_id: 'live_1',
                  view_type: 'worldmap',
                  view: { type: 'worldmap', lat: 51, lng: 10, zoom: 5 },
                  click_action: 'link',
                  object_count: 3
                }
              },
              links: []
            }
          ],
          links: []
        })
      )
    )

    const maps = await api.list()

    expect(maps).toHaveLength(1)
    expect(maps[0]).toMatchObject({
      name: 'map1',
      view_type: 'worldmap',
      view: { type: 'worldmap', lat: 51, lng: 10, zoom: 5 },
      object_count: 3,
      owner: 'alice',
      can_edit: true,
      can_delete: false,
      public: ['contact_groups', ['ops']],
      // Sparse summary fields fall back to their MapRead defaults.
      icon_size: null,
      rotation_interval: 0,
      show_in_lists: true
    })
  })

  it('fetches a map and decodes the GUI-signed map from extensions', async () => {
    server.use(
      http.get('*/api/internal/objects/map/map1', () =>
        HttpResponse.json({
          domainType: 'map',
          id: 'map1',
          title: 'Map One',
          extensions: {
            owner: 'alice',
            visibility: { publish: 'private' },
            is_builtin: false,
            can_edit: true,
            can_delete: true,
            config: staticMap,
            config_b64: base64url(staticMap),
            sig: 'deadbeef'
          },
          links: []
        })
      )
    )

    const signed = await api.get('map1')

    expect(signed.owner).toBe('alice')
    expect(signed.sig).toBe('deadbeef')
    expect(signed.config).toEqual(staticMap)
  })

  it('creates a map with a JSON POST to the collection', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.post('*/api/internal/domain-types/map/collections/all', async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json({
          domainType: 'map',
          id: 'map1',
          title: 'x',
          extensions: {},
          links: []
        })
      })
    )

    await api.create(staticMap, true)

    expect(seen[0]!.method).toBe('POST')
    expect(JSON.parse(seen[0]!.body)).toEqual({
      config: staticMap,
      visibility: { publish: 'all' }
    })
  })

  it('surfaces a duplicate-name conflict with its status so the create dialog can show it', async () => {
    server.use(
      http.post('*/api/internal/domain-types/map/collections/all', () =>
        HttpResponse.json(
          {
            title: "The map 'map1' already exists.",
            detail: 'Use the update endpoint to modify an existing map.',
            status: 409
          },
          { status: 409 }
        )
      )
    )

    await expect(api.create(staticMap, true)).rejects.toMatchObject({
      name: 'CmkApiError',
      statusCode: 409
    })
  })

  it('updates a map with PUT + If-Match: * and preserves visibility when omitted', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.put('*/api/internal/objects/map/map1', async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json({
          domainType: 'map',
          id: 'map1',
          title: 'x',
          extensions: {},
          links: []
        })
      })
    )

    await api.update(staticMap)

    expect(seen[0]!.method).toBe('PUT')
    expect(seen[0]!.headers.get('If-Match')).toBe('*')
    expect(JSON.parse(seen[0]!.body)).toEqual({ config: staticMap })
  })

  it('strips transient auto:* and site objects from the persisted wire config', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.put('*/api/internal/objects/map/map1', async ({ request }) => {
        seen.push(await snapshot(request))
        return HttpResponse.json({
          domainType: 'map',
          id: 'map1',
          title: 'x',
          extensions: {},
          links: []
        })
      })
    )

    // ``currentMap`` merges the daemon's inflated worldmap hosts (synthetic
    // ``auto:*`` ids) and the client-only ``site`` roots for rendering; neither
    // may reach the store, else the live host set freezes into the saved config.
    const curated = { id: 'host1', type: 'host', host_name: 'host1' }
    const mapWithTransient = {
      ...staticMap,
      objects: [
        curated,
        { id: 'auto:host2', type: 'host', host_name: 'host2' },
        { id: 'site1', type: 'site', host_name: 'site1' }
      ]
    } as MapConfig

    await api.update(mapWithTransient)

    // The wire config groups each object's flat fields into nested sub-objects
    // (``position``/``link`` always present, ``binding`` etc. only when set), so
    // the curated object crosses as its nested shape.
    expect(JSON.parse(seen[0]!.body)).toEqual({
      config: {
        ...staticMap,
        objects: [
          { id: 'host1', type: 'host', position: {}, link: {}, binding: { host_name: 'host1' } }
        ]
      }
    })
  })

  it('deletes a map with DELETE + If-Match: *', async () => {
    const seen: SeenRequest[] = []
    server.use(
      http.delete('*/api/internal/objects/map/map1', async ({ request }) => {
        seen.push(await snapshot(request))
        return new HttpResponse(null, { status: 204 })
      })
    )

    await api.delete('map1')

    expect(seen[0]!.method).toBe('DELETE')
    expect(seen[0]!.headers.get('If-Match')).toBe('*')
  })
})
