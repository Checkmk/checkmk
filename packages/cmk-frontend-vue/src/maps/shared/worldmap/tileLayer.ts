/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Where a geo map's tiles come from — the one place in the SPA that knows.
 *
 * The browser fetches the tiles directly (same as NagVis' worldmap), so a site
 * on a bandwidth-limited or air-gapped network points ``WorldmapView.tile_url``
 * (or the site-wide default) at its own OSM-compatible server and NOTHING may
 * bypass that: the map canvas and the list thumbnails resolve the URL, the
 * attribution and the saturation through this module, so a per-map override
 * reaches every place tiles are drawn.
 *
 * Which servers exist, and which ones the page's content security policy allows,
 * is the site's answer (``MapsTileSource``, read with the authoring settings) --
 * a second copy here would fail as a blank canvas the day the two drift.
 */
import L from 'leaflet'

import type { MapView, TileSource, WorldmapView } from '@/maps/types/api'

function tileHost(url: string): string | null {
  return /^https?:\/\/([^/?#]+)/i.exec(url.trim())?.[1]?.toLowerCase() ?? null
}

function hostMatches(host: string, allowed: string): boolean {
  // A wildcard source stands for any subdomain, which is also what Leaflet's
  // ``{s}`` placeholder expands into.
  const wildcard = allowed.startsWith('*.')
  return wildcard ? host.endsWith(allowed.slice(1)) : host === allowed
}

/**
 * Whether the page policy lets the browser load tiles from *url*.
 *
 * ``allowedSources`` is what the site says (``MapsTileSource.allowed_sources``):
 * a URL pointing anywhere else renders an empty canvas, so the map settings say
 * so rather than let the operator guess.
 */
export function isAllowedTileUrl(url: string, allowedSources: string[]): boolean {
  const host = tileHost(url)
  if (host === null) {
    return false
  }
  return allowedSources.some((source) => {
    const allowed = tileHost(source)
    return allowed !== null && hostMatches(host, allowed)
  })
}

/** Required by the OSM tile usage policy, hence not optional anywhere. */
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

export interface TileSettings {
  url: string
  attribution: string
  /** CSS filter for the tile pane, empty when the map keeps the tiles as they are. */
  paneFilter: string
}

function worldmapView(view: MapView | null | undefined): WorldmapView | null {
  return view?.type === 'worldmap' ? view : null
}

/**
 * The map's own server where it names one, the site's otherwise. ``url`` is empty
 * until the site's tile source has been read, and nothing is drawn on an empty
 * one -- a guessed default is what would reach openstreetmap.org from an
 * air-gapped installation.
 */
export function tileSettings(
  view: MapView | null | undefined,
  site: TileSource | null
): TileSettings {
  const wv = worldmapView(view)
  const saturate = wv?.tile_saturate
  return {
    url: wv?.tile_url || site?.default_url || '',
    attribution: OSM_ATTRIBUTION,
    paneFilter: saturate === null || saturate === undefined ? '' : `saturate(${saturate}%)`
  }
}

/**
 * Adds the map's tile layer and applies its saturation, replacing a layer added
 * by an earlier call.
 */
export function applyTileLayer(
  leafletMap: L.Map,
  view: MapView | null | undefined,
  site: TileSource | null,
  previous: L.TileLayer | null = null
): L.TileLayer | null {
  const settings = tileSettings(view, site)
  if (!settings.url) {
    return previous
  }
  previous?.remove()
  const layer = L.tileLayer(settings.url, { attribution: settings.attribution }).addTo(leafletMap)
  const pane = leafletMap.getPane('tilePane')
  if (pane) {
    pane.style.filter = settings.paneFilter
  }
  return layer
}
