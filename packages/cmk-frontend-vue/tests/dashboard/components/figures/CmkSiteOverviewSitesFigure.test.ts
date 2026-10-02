/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkSiteOverviewSitesFigure from '@/dashboard/components/figures/CmkSiteOverviewSitesFigure.vue'
import type { SiteOverviewSites } from '@/dashboard/types/widget'

const SITES: SiteOverviewSites = {
  mode: 'sites',
  links: [
    {
      title: 'Site',
      location: { type: 'dashboards', name: 'site' },
      include_context: true,
      include_time_range: false,
      show_filter_form: false
    }
  ],
  sites: [
    {
      status: 'online',
      site_id: 'heute',
      alias: 'Local site',
      parts: [
        { category: 'critical', count: 1 },
        { category: 'unknown', count: 0 },
        { category: 'warning', count: 0 },
        { category: 'downtime', count: 0 },
        { category: 'ok', count: 4 }
      ],
      link_properties: {
        links: [{ siteopt: { status: 'encoded', variables: { site: 'heute' } } }]
      }
    },
    { status: 'down', site_id: 'remote', alias: 'Remote site' }
  ]
}

function renderFigure(interactive = true, value: SiteOverviewSites = SITES) {
  return render(CmkSiteOverviewSitesFigure, {
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

describe('CmkSiteOverviewSitesFigure', () => {
  it('renders an anchor for every online site and none for a site that is down', () => {
    renderFigure()

    expect(screen.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      expect.stringContaining('site=heute')
    ])
  })

  it('labels every site with its alias', () => {
    renderFigure()

    expect(screen.getByText('Local site')).toBeInTheDocument()
    expect(screen.getByText('Remote site')).toBeInTheDocument()
  })

  it('shows the host counts of a hovered site in a tooltip', async () => {
    renderFigure()

    await fireEvent.pointerMove(screen.getByRole('link'))

    expect(await screen.findByText('hosts in total')).toBeInTheDocument()
  })

  it('shows the missing icon for a site with an unknown status', () => {
    const { container } = renderFigure(true, {
      ...SITES,
      sites: [{ status: 'unknown', site_id: 'remote', alias: 'Remote site' }]
    })

    expect(container.querySelector('image')).toHaveAttribute(
      'href',
      expect.stringContaining('icon_site_missing')
    )
  })

  it('renders no site anchor when not interactive', () => {
    renderFigure(false)

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '400')
    expect(svg).toHaveAttribute('height', '200')
    expect(svg).toHaveAttribute('viewBox', '0 0 400 200')
  })
})
