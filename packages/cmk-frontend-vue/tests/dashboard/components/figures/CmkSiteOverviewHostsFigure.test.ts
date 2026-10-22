/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
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

const TWO_LINKS: SiteOverviewHosts = {
  ...HOSTS,
  links: [...HOSTS.links, { ...HOSTS.links[0]!, title: 'Services' }],
  hosts: HOSTS.hosts.map((entry) => ({
    ...entry,
    link_properties: { links: [...entry.link_properties.links, ...entry.link_properties.links] }
  }))
}

function renderFigure(value: SiteOverviewHosts = HOSTS) {
  return render(CmkSiteOverviewHostsFigure, {
    props: {
      value,
      width: 400,
      height: 200,
      hexagonSize: 'default',
      filters: {}
    }
  })
}

async function hoverFirstHost(): Promise<void> {
  const [area] = document.querySelectorAll('rect')
  await fireEvent.pointerMove(area!, { clientX: 44, clientY: 49 })
}

async function openFirstHostMenu(): Promise<void> {
  await hoverFirstHost()
  screen.getByRole('button', { name: 'alpha' }).focus()
  await userEvent.keyboard('{Enter}')
  await screen.findByRole('menu')
  await screen.findByText('Host is up')
}

function highlights(): Element[] {
  return [...document.querySelectorAll('.db-hexagon-grid-figure__highlight')]
}

describe('CmkSiteOverviewHostsFigure', () => {
  it('highlights the hovered host only', async () => {
    renderFigure()

    await hoverFirstHost()

    expect(highlights()).toHaveLength(1)
  })

  it('removes the highlight once the pointer leaves', async () => {
    renderFigure()
    await hoverFirstHost()

    await fireEvent.pointerLeave(document.querySelector('svg g')!)

    expect(highlights()).toHaveLength(0)
  })

  it('keeps the tooltip and the menu of a host after the pointer leaves', async () => {
    renderFigure(TWO_LINKS)
    await openFirstHostMenu()

    await fireEvent.pointerLeave(document.querySelector('svg g')!)

    expect(screen.getByRole('menu')).toBeInTheDocument()
    expect(screen.getByText('Host is up')).toBeInTheDocument()
  })

  it('lets the tooltip go once a refresh takes the menu of a host away', async () => {
    const { rerender } = renderFigure(TWO_LINKS)
    await openFirstHostMenu()

    await rerender({ value: HOSTS })

    expect(screen.queryByText('Host is up')).toBeNull()
  })

  it('closes the menu of a host once a refresh puts another host in its place', async () => {
    const { rerender } = renderFigure(TWO_LINKS)
    await openFirstHostMenu()

    await rerender({ value: { ...TWO_LINKS, hosts: [...TWO_LINKS.hosts].reverse() } })

    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('closes the menu and the tooltip of a host on Escape', async () => {
    renderFigure(TWO_LINKS)
    await openFirstHostMenu()

    await userEvent.keyboard('{Escape}')

    expect(screen.queryByRole('menu')).toBeNull()
    expect(screen.queryByText('Host is up')).toBeNull()
  })

  it('marks the tooltip of a host with several links with the menu arrow', async () => {
    renderFigure(TWO_LINKS)

    await hoverFirstHost()

    expect(
      (await screen.findByText('Host is up'))
        .closest('.cmk-pointer-tooltip')!
        .querySelector('.db-contextual-link-anchor__arrow')
    ).not.toBeNull()
  })

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

  it('draws the inner hexagons above the outer hexagons of every state', () => {
    const { container } = renderFigure({
      ...HOSTS,
      hosts: [host('alpha'), host('beta', { num_warn: 2 }), host('gamma', { num_crit: 1 })]
    })

    const fills = [...container.querySelectorAll('path')].map((path) => path.style.fill)
    expect(fills.at(-1)).toBe('var(--background-muted)')
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '400')
    expect(svg).toHaveAttribute('height', '200')
    expect(svg).toHaveAttribute('viewBox', '0 0 400 200')
  })
})
