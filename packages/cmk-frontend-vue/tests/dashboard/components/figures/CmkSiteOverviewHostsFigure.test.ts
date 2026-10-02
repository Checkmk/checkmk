/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkSiteOverviewHostsFigure from '@/dashboard/components/figures/CmkSiteOverviewHostsFigure.vue'
import type { SiteOverviewHost, SiteOverviewHosts } from '@/dashboard/types/widget'

function host(hostName: string, overrides: Partial<SiteOverviewHost> = {}): SiteOverviewHost {
  return {
    site_id: 'heute',
    host_name: hostName,
    state: 'UP',
    has_been_checked: true,
    in_downtime: false,
    num_services: 10,
    num_warn: 0,
    num_crit: 0,
    num_unknown: 0,
    link_properties: {
      links: [
        {
          siteopt: { status: 'encoded', variables: { site: 'heute' } },
          host: { status: 'encoded', variables: { host: hostName } }
        }
      ]
    },
    ...overrides
  }
}

const HOSTS: SiteOverviewHosts = {
  mode: 'hosts',
  links: [
    {
      title: 'Host',
      location: { type: 'views', name: 'host', owner: null },
      include_context: false,
      include_time_range: false,
      show_filter_form: false
    }
  ],
  hosts: [host('alpha'), host('beta', { state: 'DOWN' })]
}

function renderFigure(interactive = true, value: SiteOverviewHosts = HOSTS) {
  return render(CmkSiteOverviewHostsFigure, {
    props: {
      value,
      width: 400,
      height: 200,
      hexagonSize: 'default',
      filters: {},
      interactive
    }
  })
}

async function hoverFirstHost(): Promise<void> {
  const [area] = document.querySelectorAll('rect')
  await fireEvent.pointerMove(area!, { clientX: 44, clientY: 49 })
}

describe('CmkSiteOverviewHostsFigure', () => {
  it('names the hosts by their state in its accessible name', () => {
    renderFigure()

    expect(screen.getByRole('figure')).toHaveAccessibleName('2 hosts, 1 OK, 1 down')
  })

  it('renders an anchor to the hovered host', async () => {
    renderFigure()

    await hoverFirstHost()

    expect(screen.getByRole('link', { name: 'alpha' })).toHaveAttribute(
      'href',
      expect.stringContaining('host=alpha')
    )
  })

  it('shows the hovered host in a tooltip', async () => {
    renderFigure()

    await hoverFirstHost()

    expect(await screen.findByText('Host is up')).toBeInTheDocument()
  })

  it('renders no anchor to a hovered host when not interactive', async () => {
    renderFigure(false)

    await hoverFirstHost()

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('draws the inner hexagons above the outer hexagons of every state', () => {
    const { container } = renderFigure(true, {
      ...HOSTS,
      hosts: [host('alpha'), host('beta', { num_warn: 2 }), host('gamma', { num_crit: 1 })]
    })

    const fills = [...container.querySelectorAll('path')].map((path) => path.style.fill)
    expect(fills.at(-1)).toBe('var(--db-cmk-site-overview-hosts-figure-headline)')
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '400')
    expect(svg).toHaveAttribute('height', '200')
    expect(svg).toHaveAttribute('viewBox', '0 0 400 200')
  })
})
