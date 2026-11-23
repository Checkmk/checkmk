/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import MapLiveIndicator from '@/maps/map/components/MapLiveIndicator.vue'

import { fakeMapsServices, mapsGlobal } from '../../support/services'

describe('MapLiveIndicator', () => {
  // The blink is a CSS animation that plays once per element, so a new dot per
  // update is what makes it blink again; jsdom runs no animations to observe.
  it('draws a new dot for every update that arrives', async () => {
    const services = fakeMapsServices()
    services.states.lastUpdate.value = 1
    const { container } = render(MapLiveIndicator, {
      props: { status: 'live' },
      global: mapsGlobal({}, services)
    })
    const dot = () => container.querySelector('.maps-map-live-indicator__dot')
    const before = dot()

    services.states.lastUpdate.value = 2
    await nextTick()

    expect(dot()).not.toBe(before)
  })
})
