/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapStateAlert from '@/maps/map/components/MapStateAlert.vue'

describe('MapStateAlert', () => {
  it('names the unreachable sites and what became of their hosts', () => {
    render(MapStateAlert, {
      props: { status: 'live', deadSites: ['paris', 'nyc'], deadSiteHosts: 'missing' }
    })

    expect(
      screen.getByText('Site unreachable: paris, nyc — its hosts are missing from the map')
    ).toBeInTheDocument()
  })

  // Without the daemon nothing about the sites is current either.
  it('says the connection is lost rather than which sites are unreachable', () => {
    render(MapStateAlert, {
      props: { status: 'lost', deadSites: ['paris'], deadSiteHosts: 'no-state' }
    })

    expect(screen.getByText('Connection lost — showing last known state')).toBeInTheDocument()
    expect(screen.queryByText(/Site unreachable/)).toBeNull()
  })

  it('claims no last known state when none ever arrived', () => {
    render(MapStateAlert, {
      props: { status: 'unreachable', deadSites: [], deadSiteHosts: 'no-state' }
    })

    expect(screen.getByText('No connection — states unknown')).toBeInTheDocument()
  })

  it.each(['live', 'connecting'] as const)('says nothing while %s', (status) => {
    const { container } = render(MapStateAlert, {
      props: { status, deadSites: [], deadSiteHosts: 'no-state' }
    })

    expect(container.textContent).toBe('')
  })
})
