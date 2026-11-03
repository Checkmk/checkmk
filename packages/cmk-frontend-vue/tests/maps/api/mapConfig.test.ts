/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { MapConfigApi } from '@/maps/api/mapConfig'
import { toWireConfig } from '@/maps/api/wire'
import type { MapConfig } from '@/maps/types/api'

import { aMap, newMapView } from '../support/fixtures'
import { type SeenRequest, snapshot } from '../support/http'

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

  const storedMap: components['schemas']['MapObject'] = {
    domainType: 'map',
    id: 'map1',
    title: 'Map One',
    extensions: {
      owner: 'alice',
      visibility: { publish: 'private', hide_in_monitor_menu: false },
      is_builtin: false,
      can_edit: true,
      can_delete: true,
      config: toWireConfig(staticMap),
      config_b64: base64url(staticMap),
      sig: 'deadbeef',
      map_link_titles: {}
    },
    links: []
  }

  it('lists maps and flattens the domain collection into MapRead rows', async () => {
    server.use(
      restApiHttp.get('/domain-types/map/collections/all', ({ response }) =>
        response(200).json({
          id: 'map',
          domainType: 'map',
          value: [
            {
              domainType: 'map',
              id: 'map1',
              title: 'Map One',
              extensions: {
                owner: 'alice',
                visibility: {
                  publish: 'contact_groups',
                  groups: ['ops'],
                  hide_in_monitor_menu: true
                },
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
      hide_in_monitor_menu: true,
      // Sparse summary fields fall back to their MapRead defaults.
      icon_size: null,
      rotation_interval: 0
    })
  })

  it('fetches a map and decodes the GUI-signed map from extensions', async () => {
    server.use(
      restApiHttp.get('/objects/map/{name}', ({ response }) => response(200).json(storedMap))
    )

    const signed = await api.get('map1')

    expect(signed.owner).toBe('alice')
    expect(signed.sig).toBe('deadbeef')
    expect(signed.config).toEqual(staticMap)
  })

  it('creates a map with a JSON POST to the collection', async () => {
    const seen: SeenRequest[] = []
    server.use(
      restApiHttp.post('/domain-types/map/collections/all', async ({ request, response }) => {
        seen.push(await snapshot(request))
        return response(200).json(storedMap)
      })
    )

    await api.create(staticMap, { public: true, hide_in_monitor_menu: true })

    expect(seen[0]!.method).toBe('POST')
    expect(JSON.parse(seen[0]!.body)).toEqual({
      config: staticMap,
      visibility: { publish: 'all', hide_in_monitor_menu: true }
    })
  })

  it('surfaces a duplicate-name conflict with its status so the create dialog can show it', async () => {
    server.use(
      restApiHttp.post('/domain-types/map/collections/all', ({ response }) =>
        response.untyped(
          HttpResponse.json(
            {
              title: "The map 'map1' already exists",
              detail: 'Use the update endpoint to modify an existing map.',
              status: 409
            },
            { status: 409 }
          )
        )
      )
    )

    await expect(
      api.create(staticMap, { public: true, hide_in_monitor_menu: false })
    ).rejects.toMatchObject({
      name: 'CmkApiError',
      statusCode: 409
    })
  })

  it('updates a map with PUT + If-Match: * and preserves visibility when omitted', async () => {
    const seen: SeenRequest[] = []
    server.use(
      restApiHttp.put('/objects/map/{name}', async ({ request, response }) => {
        seen.push(await snapshot(request))
        return response(200).json(storedMap)
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
      restApiHttp.put('/objects/map/{name}', async ({ request, response }) => {
        seen.push(await snapshot(request))
        return response(200).json(storedMap)
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
      restApiHttp.delete('/objects/map/{name}', async ({ request, response }) => {
        seen.push(await snapshot(request))
        return response(204).empty()
      })
    )

    await api.delete('map1')

    expect(seen[0]!.method).toBe('DELETE')
    expect(seen[0]!.headers.get('If-Match')).toBe('*')
  })
})
