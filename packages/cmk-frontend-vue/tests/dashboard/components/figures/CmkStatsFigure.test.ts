/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkStatsFigure from '@/dashboard/components/figures/CmkStatsFigure.vue'
import type { LinkProperties, Stats } from '@/dashboard/types/widget'

function hostStateKey(variable: string): LinkProperties {
  return { links: [{ hoststate: { status: 'encoded', variables: { [variable]: 'on' } } }] }
}

const HOST_STATS: Stats = {
  links: [
    {
      title: 'All hosts',
      location: { type: 'views', name: 'searchhost' },
      include_context: true,
      include_time_range: false,
      show_filter_form: true
    }
  ],
  parts: [
    { category: 'up', count: 12, link_properties: hostStateKey('hst0') },
    { category: 'downtime', count: 1, link_properties: { links: [{}] } },
    { category: 'unreachable', count: 0, link_properties: hostStateKey('hst2') },
    { category: 'down', count: 2, link_properties: hostStateKey('hst1') }
  ],
  total: { count: 15, link_properties: { links: [{}] } }
}

function renderFigure(interactive = true) {
  return render(CmkStatsFigure, {
    props: { value: HOST_STATS, width: 400, height: 200, filters: {}, interactive }
  })
}

describe('CmkStatsFigure', () => {
  it('draws one ring per part with a count', () => {
    renderFigure()

    expect(screen.getAllByRole('img').map((ring) => ring.getAttribute('aria-label'))).toEqual([
      'Up: 12',
      'In downtime: 1',
      'Down: 2'
    ])
  })

  it('wraps every linkable part in the contextual link trigger', () => {
    renderFigure()

    expect(screen.getByRole('link', { name: /Down/ }).getAttribute('href')).toBe(
      'view.py?view_name=searchhost&hst1=on&filled_in=filter&_show_filter_form=1'
    )
    expect(screen.getAllByRole('link')).toHaveLength(5)
  })

  it('renders no anchor when not interactive', () => {
    renderFigure(false)

    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '400')
    expect(svg).toHaveAttribute('height', '200')
    expect(svg).toHaveAttribute('viewBox', '0 0 400 200')
  })
})
