/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkInventoryFigure from '@/dashboard/components/figures/CmkInventoryFigure.vue'
import type { InventoryAttribute } from '@/dashboard/types/widget'

const ATTRIBUTE: InventoryAttribute = {
  links: [
    {
      title: 'Inventory of host',
      location: { type: 'views', name: 'inv_host' },
      include_context: false,
      include_time_range: false,
      show_filter_form: false
    }
  ],
  link_properties: {
    links: [
      {
        siteopt: { status: 'encoded', variables: { site: 'heute' } },
        host: { status: 'encoded', variables: { host: 'myhost' } }
      }
    ]
  },
  value: 'Ubuntu 24.04'
}

function renderFigure(value: Partial<InventoryAttribute> = {}, interactive = true) {
  return render(CmkInventoryFigure, {
    props: {
      value: { ...ATTRIBUTE, ...value },
      width: 300,
      height: 150,
      filters: {},
      interactive
    }
  })
}

describe('CmkInventoryFigure', () => {
  it('draws the attribute as the server renders it', () => {
    renderFigure()

    expect(screen.getByText('Ubuntu 24.04')).toBeInTheDocument()
  })

  it('draws the not-available text for a host without the attribute', () => {
    renderFigure({ value: null })

    expect(screen.getByText('n/a')).toBeInTheDocument()
  })

  it('wraps the attribute in the contextual link trigger', () => {
    renderFigure()

    expect(screen.getByRole('link')).toHaveTextContent('Ubuntu 24.04')
  })

  it('renders no anchor when not interactive', () => {
    renderFigure({}, false)

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '300')
    expect(svg).toHaveAttribute('height', '150')
    expect(svg).toHaveAttribute('viewBox', '0 0 300 150')
  })
})
