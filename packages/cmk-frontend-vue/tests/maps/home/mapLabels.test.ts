/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { hasDynamicContent } from '@/maps/home/mapLabels'
import { newMapView } from '@/maps/utils/model'

import { aListedMap } from '../support/fixtures'

describe('hasDynamicContent', () => {
  it('is true for the map types whose objects come from the live query', () => {
    for (const type of ['flow', 'radar', 'worldmap'] as const) {
      expect(hasDynamicContent(aListedMap({ view: newMapView(type) }))).toBe(true)
    }
  })

  it('is false for the map types whose objects are placed by hand', () => {
    for (const type of ['static', 'presentation'] as const) {
      expect(hasDynamicContent(aListedMap({ view: newMapView(type) }))).toBe(false)
    }
  })

  it('does not treat a built-in map as dynamic', () => {
    // Not editable is a different question: the shipped NOC wall is a
    // presentation map with hand-placed elements, and it has a count to show
    // like any other.
    const builtin = aListedMap({
      view: newMapView('presentation'),
      is_builtin: true,
      can_edit: false
    })

    expect(hasDynamicContent(builtin)).toBe(false)
  })
})
