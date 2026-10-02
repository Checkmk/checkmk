/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkAlertOverviewFigure from '@/dashboard/components/figures/CmkAlertOverviewFigure.vue'
import type { AlertOverview, AlertOverviewElement } from '@/dashboard/types/widget'

function element(
  hostName: string,
  serviceDescription: string | null,
  viewName: string
): AlertOverviewElement {
  return {
    site_id: 'heute',
    host_name: hostName,
    service_description: serviceDescription,
    num_ok: 0,
    num_warn: 1,
    num_crit: 2,
    num_unknown: 0,
    num_problems: 3,
    links: [
      {
        title: 'Events',
        location: { type: 'views', name: viewName },
        include_context: true,
        include_time_range: false,
        show_filter_form: false
      }
    ],
    link_properties: {
      links: [{ host: { status: 'encoded', variables: { host: hostName } } }]
    }
  }
}

const VALUE: AlertOverview = {
  elements: [
    element('myhost', 'CPU load', 'svcevents'),
    element('otherhost', null, 'hostsvcevents')
  ]
}

function renderFigure(interactive = true) {
  return render(CmkAlertOverviewFigure, {
    props: { value: VALUE, width: 400, height: 200, filters: {}, interactive }
  })
}

async function hover(clientX: number, clientY: number): Promise<void> {
  const [area] = document.querySelectorAll('rect')
  await fireEvent.pointerMove(area!, { clientX, clientY })
}

describe('CmkAlertOverviewFigure', () => {
  it('counts the objects with alerts in its accessible name', () => {
    renderFigure()

    expect(screen.getByRole('figure')).toHaveAccessibleName('2 objects with alerts')
  })

  it('links a service to its own target and a host to its own target', async () => {
    renderFigure()

    await hover(52, 61)
    expect(screen.getByRole('link', { name: 'myhost - CPU load' })).toHaveAttribute(
      'href',
      expect.stringContaining('view_name=svcevents')
    )

    await hover(148, 61)
    expect(screen.getByRole('link', { name: 'otherhost' })).toHaveAttribute(
      'href',
      expect.stringContaining('view_name=hostsvcevents')
    )
  })

  it('shows the alert counts of the hovered object in a tooltip', async () => {
    renderFigure()

    await hover(52, 61)

    expect(await screen.findByText('Problems in total')).toBeInTheDocument()
  })

  it('renders no anchor when not interactive', async () => {
    renderFigure(false)

    await hover(52, 61)

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
