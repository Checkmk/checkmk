/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Reading and writing map configuration.
 *
 * A map is a Checkmk visual, so its CRUD is the GUI's: the internal REST API
 * applies the pagetype permission model (own / foreign / built-in) by name, and
 * the calls ride the GUI session like every other page. The daemon owns only
 * live state and never stores a map.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import { uploadedFile } from '@/maps/api/upload'
import { mapListObjectToRead, mapRequestBody } from '@/maps/api/wire'
import type { CfgImport, MapConfig, MapPublic, MapRead } from '@/maps/types/api'

/**
 * A map as the daemon must receive it: the exact bytes the GUI signed, so a
 * viewer cannot substitute a tampered config for a foreign map, plus those bytes
 * parsed for rendering. ``config`` is never re-serialised back into a request.
 */
export interface SignedMap {
  config: MapConfig
  config_b64: string
  sig: string
  owner: string
  /**
   * Titles of the maps this map links to, keyed by map id, resolved by the GUI
   * against the viewer's permissions. It travels beside the signed bytes, never
   * inside them: the signature covers the stored config.
   */
  map_link_titles: Record<string, string>
}

/** The signed map as it crosses the wire, in the show response's ``extensions``. */
export interface RawSignedMap {
  config_b64: string
  sig: string
  owner: string
  map_link_titles?: Record<string, string>
}

/**
 * Decodes a base64url (unpadded, ``-``/``_``) payload to a UTF-8 string. Map
 * aliases and labels may be non-ASCII, so this goes through bytes.
 */
function b64urlToString(b64url: string): string {
  const b64 = b64url.replace(/-/g, '+').replace(/_/g, '/')
  const padded = b64.padEnd(Math.ceil(b64.length / 4) * 4, '=')
  const bin = atob(padded)
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)))
}

export function decodeSignedMap(raw: RawSignedMap): SignedMap {
  return {
    config: JSON.parse(b64urlToString(raw.config_b64)) as MapConfig,
    config_b64: raw.config_b64,
    sig: raw.sig,
    owner: raw.owner,
    map_link_titles: raw.map_link_titles ?? {}
  }
}

export class MapConfigApi {
  /** Creates a map owned by the session user. Visibility is clamped server-side. */
  public async create(map: MapConfig, visibility?: MapPublic): Promise<void> {
    unwrap(
      await client.POST('/domain-types/map/collections/all', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: mapRequestBody(map, visibility)
      })
    )
  }

  /**
   * Updates a map in place.
   *
   * The server resolves it by name and applies the permission model — an own map
   * is updated, a foreign one edited in place, a built-in customized into an own
   * override — so no owner travels with the request. Omitting ``visibility``
   * preserves the stored sharing scope, which is what a routine autosave wants.
   * ``If-Match: *`` opts out of optimistic locking: the SPA is the only editing
   * surface and carries the map's own ``version``.
   */
  public async update(map: MapConfig, visibility?: MapPublic): Promise<void> {
    unwrap(
      await client.PUT('/objects/map/{name}', {
        params: {
          path: { name: map.name },
          header: { 'If-Match': '*', 'Content-Type': 'application/json' }
        },
        body: mapRequestBody(map, visibility)
      })
    )
  }

  public async list(): Promise<MapRead[]> {
    const collection = unwrap(await client.GET('/domain-types/map/collections/all'))
    return collection.value.map(mapListObjectToRead)
  }

  public async get(name: string): Promise<SignedMap> {
    const map = unwrap(await client.GET('/objects/map/{name}', { params: { path: { name } } }))
    // ``extensions`` carries {config_b64, sig, owner}: the typed
    // ``extensions.config`` is deliberately not re-serialised, so the daemon
    // verifies exactly what the GUI signed.
    return decodeSignedMap(map.extensions)
  }

  /** Deletes a map. Built-ins are refused and a foreign map needs the permission. */
  public async delete(name: string): Promise<void> {
    unwrap(
      await client.DELETE('/objects/map/{name}', {
        params: { path: { name }, header: { 'If-Match': '*' } }
      })
    )
  }

  /**
   * Uploads a map background. Only the file is stored here; the map's
   * ``background_image`` field is persisted by the map save, so the caller adopts
   * the returned (capability-carrying) filename.
   */
  public async uploadBackground(mapName: string, file: File): Promise<{ filename: string }> {
    return unwrap(
      await client.POST('/objects/map/{name}/actions/upload-background/invoke', {
        params: { path: { name: mapName }, header: { 'Content-Type': 'application/json' } },
        body: await uploadedFile(file)
      })
    )
  }

  public async deleteBackground(mapName: string): Promise<void> {
    unwrap(
      await client.POST('/objects/map/{name}/actions/delete-background/invoke', {
        params: { path: { name: mapName } }
      })
    )
  }

  /**
   * Parses a NagVis ``.cfg`` into a map without storing it — the format knowledge
   * is the GUI's. The result is a draft the editor shows before the user saves,
   * plus the connection remaps the importer had to guess.
   */
  public async parseCfg(file: File): Promise<CfgImport> {
    const { filename, content } = await uploadedFile(file)
    const parsed = unwrap(
      await client.POST('/domain-types/map/actions/parse-cfg/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: { filename, content }
      })
    )
    // The draft is the map document itself, which the REST layer carries opaquely:
    // a map's shape is validated by the daemon, the GUI only stores and forwards
    // it. It is the same shape the editor works in.
    return { map: parsed.map as unknown as MapConfig, warnings: parsed.warnings }
  }
}
