/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { objectIconSize } from '@/maps/map/objectIconSize'
import { newMapElement } from '@/maps/utils/model'

const SIZES = { map: 40, override: undefined, fallback: 20 }

describe('objectIconSize', () => {
  it("takes the object's own size where it has one", () => {
    const object = newMapElement({
      id: '1',
      type: 'host',
      display: { mode: 'icon', image_size: 90 }
    })
    expect(objectIconSize(object, SIZES)).toBe(90)
  })

  it('gives a gadget the room an instrument needs to be readable', () => {
    const object = newMapElement({ id: '1', type: 'host', display: { mode: 'gadget' } })
    expect(objectIconSize(object, SIZES)).toBeGreaterThan(SIZES.map)
  })

  it("falls back to the map's setting, then to the site's", () => {
    const object = newMapElement({ id: '1', type: 'host' })
    expect(objectIconSize(object, SIZES)).toBe(40)
    expect(objectIconSize(object, { ...SIZES, map: null })).toBe(20)
  })

  it('lets a caller override the map, as the settings preview does', () => {
    const object = newMapElement({ id: '1', type: 'host' })
    expect(objectIconSize(object, { ...SIZES, override: 12 })).toBe(12)
  })
})
