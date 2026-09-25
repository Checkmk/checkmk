/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useMapObjectMenus } from '@/maps/map/composables/useMapObjectMenus'

import { anObject } from '../../support/fixtures'
import { fakeMapsServices, runWithServices } from '../../support/services'

function menusOnAMap() {
  return runWithServices(fakeMapsServices(), () =>
    useMapObjectMenus({ config: () => null, stateOf: () => undefined, preview: () => false })
  )
}

const web01 = anObject({ id: 'web01', type: 'host', host_name: 'web01' })
const db01 = anObject({ id: 'db01', type: 'host', host_name: 'db01' })
const pointer = new MouseEvent('contextmenu', { clientX: 300, clientY: 200 })

describe('useMapObjectMenus', () => {
  it('closes the hover card when the context menu opens', () => {
    const menus = menusOnAMap()
    menus.openHover(web01, pointer)
    expect(menus.hover.hover.visible).toBe(true)

    menus.openContext(web01, pointer)

    expect(menus.hover.hover.visible).toBe(false)
    expect(menus.context.visible).toBe(true)
  })

  it('opens no hover card over an open context menu', () => {
    const menus = menusOnAMap()
    menus.openContext(web01, pointer)

    menus.openHover(db01, pointer)

    expect(menus.hover.hover.visible).toBe(false)
  })
})
