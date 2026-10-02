/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkStateSummaryFigure from '@/dashboard/components/figures/CmkStateSummaryFigure.vue'
import type { StateSummary } from '@/dashboard/types/widget'

const SUMMARY: StateSummary = {
  links: [
    {
      title: 'All hosts',
      location: { type: 'views', name: 'searchhost', owner: null },
      include_context: true,
      include_time_range: false,
      show_filter_form: false
    }
  ],
  in_state: {
    count: 3,
    link_properties: {
      links: [{ hoststate: { status: 'encoded', variables: { hst1: 'on' } } }]
    }
  },
  total: 10
}

function renderFigure(interactive = true) {
  return render(CmkStateSummaryFigure, {
    props: { value: SUMMARY, width: 300, height: 200, filters: {}, interactive }
  })
}

describe('CmkStateSummaryFigure', () => {
  it('draws the count in the state over the total', () => {
    renderFigure()

    expect(screen.getByText('3/10')).toBeInTheDocument()
  })

  it('links the whole summary to the objects in the state', () => {
    renderFigure()

    const link = screen.getByRole('link')
    expect(link).toHaveTextContent('3/10')
    expect(link.getAttribute('href')).toContain('hst1=on')
  })

  it('renders no anchor when not interactive', () => {
    renderFigure(false)

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '300')
    expect(svg).toHaveAttribute('height', '200')
    expect(svg).toHaveAttribute('viewBox', '0 0 300 200')
  })
})
