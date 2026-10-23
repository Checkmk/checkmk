/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { deadSiteHostsOf } from '@/maps/map/components/deadSites'
import type { MapView } from '@/maps/types/api'
import { newMapView } from '@/maps/utils/model'

describe('deadSiteHostsOf', () => {
  it('replays the last known state on a folder tree', () => {
    expect(deadSiteHostsOf(newMapView('foldertree'))).toBe('last-known')
  })

  it('drops the hosts of a radar', () => {
    expect(deadSiteHostsOf(newMapView('radar'))).toBe('missing')
  })

  it('drops the hosts of an automap', () => {
    const automap: MapView = {
      type: 'worldmap',
      lat: 51,
      lng: 10,
      zoom: 5,
      auto_source: 'all_hosts',
      auto_filter_value: '',
      problems_only: false
    }

    expect(deadSiteHostsOf(automap)).toBe('missing')
  })

  it('keeps placed objects without a state', () => {
    expect(deadSiteHostsOf(newMapView('static'))).toBe('no-state')
  })
})
