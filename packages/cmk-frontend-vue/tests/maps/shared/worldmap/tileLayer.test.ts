/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { isAllowedTileUrl, tileSettings } from '@/maps/shared/worldmap/tileLayer'
import type { TileSource, WorldmapView } from '@/maps/types/api'

import { newMapView } from '../../support/fixtures'

function worldmap(over: Partial<WorldmapView> = {}): WorldmapView {
  return { ...(newMapView('worldmap') as WorldmapView), ...over }
}

/** What the site answers when it has not configured a tile server of its own. */
const OSM: TileSource = {
  default_url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  allowed_sources: ['https://tile.openstreetmap.org/', 'https://*.tile.openstreetmap.org/']
}

describe('tileSettings', () => {
  it("serves the site's tile server when the map names none", () => {
    expect(tileSettings(worldmap(), OSM).url).toBe(OSM.default_url)
  })

  it("uses the map's own tile server, so an air-gapped site leaks no request", () => {
    const internal = 'https://tiles.internal/{z}/{x}/{y}.png'
    expect(tileSettings(worldmap({ tile_url: internal }), OSM).url).toBe(internal)
  })

  // Anything else would be a guessed server, and on an air-gapped installation
  // the guess is the one request that must not leave the site.
  it('draws nothing until the site has answered where its tiles come from', () => {
    expect(tileSettings(worldmap(), null).url).toBe('')
  })

  it('always attributes OpenStreetMap, as its tile policy requires', () => {
    expect(tileSettings(worldmap(), OSM).attribution).toContain('OpenStreetMap')
    expect(tileSettings(null, OSM).attribution).toContain('OpenStreetMap')
  })

  it('applies the saturation a map asked for', () => {
    expect(tileSettings(worldmap({ tile_saturate: 40 }), OSM).paneFilter).toBe('saturate(40%)')
  })

  it('leaves the tiles alone when no saturation is set', () => {
    expect(tileSettings(worldmap({ tile_saturate: null }), OSM).paneFilter).toBe('')
  })

  it('keeps a deliberate zero saturation, which turns the tiles grey', () => {
    expect(tileSettings(worldmap({ tile_saturate: 0 }), OSM).paneFilter).toBe('saturate(0%)')
  })

  it('falls back to the defaults for a map that is not a geo map', () => {
    const settings = tileSettings(newMapView('static'), OSM)
    expect(settings.url).toBe(OSM.default_url)
    expect(settings.paneFilter).toBe('')
  })
})

describe('isAllowedTileUrl', () => {
  it('allows OpenStreetMap, which the page policy carries out of the box', () => {
    expect(isAllowedTileUrl(OSM.default_url, OSM.allowed_sources)).toBe(true)
    expect(
      isAllowedTileUrl('https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', OSM.allowed_sources)
    ).toBe(true)
  })

  it('allows the server the site configured, including its subdomains', () => {
    const allowed = [...OSM.allowed_sources, 'https://*.basemaps.example.com/']
    expect(isAllowedTileUrl('https://a.basemaps.example.com/light/1/2/3.png', allowed)).toBe(true)
    expect(isAllowedTileUrl('https://tiles.internal/1/2/3.png', ['https://tiles.internal/'])).toBe(
      true
    )
  })

  it('rejects any other server, whose tiles the browser would block', () => {
    expect(isAllowedTileUrl('https://tiles.example.net/1/2/3.png', OSM.allowed_sources)).toBe(false)
    expect(isAllowedTileUrl('https://tiles.example.net/1/2/3.png', [])).toBe(false)
    // Not a tile URL at all — the settings form must flag it just the same.
    expect(isAllowedTileUrl('javascript:alert(1)', OSM.allowed_sources)).toBe(false)
  })
})
