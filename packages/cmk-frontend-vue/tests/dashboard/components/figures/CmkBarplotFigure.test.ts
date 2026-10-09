/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkBarplotFigure from '@/dashboard/components/figures/CmkBarplotFigure.vue'
import type { Barplot, BarplotBar } from '@/dashboard/types/widget'

function bar(hostName: string, value: number): BarplotBar {
  return {
    site_id: 'heute',
    host_name: hostName,
    service_description: 'CPU utilization',
    value,
    link_properties: {
      links: [
        {
          siteopt: { status: 'encoded', variables: { site: 'heute' } },
          host: { status: 'encoded', variables: { host: hostName } },
          service: { status: 'encoded', variables: { service: 'CPU utilization' } }
        }
      ]
    }
  }
}

const BARPLOT: Barplot = {
  links: [
    {
      title: 'Service',
      location: { type: 'views', name: 'service', owner: null },
      include_context: false,
      include_time_range: false,
      show_filter_form: false
    }
  ],
  unit_format: {
    notation: 'decimal',
    symbol: '%',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  range: null,
  bars: [bar('myhost', 40), bar('otherhost', 60)]
}

function renderFigure(value: Partial<Barplot> = {}, { height = 200 }: { height?: number } = {}) {
  return render(CmkBarplotFigure, {
    props: { value: { ...BARPLOT, ...value }, width: 300, height, filters: {} }
  })
}

describe('CmkBarplotFigure', () => {
  it('draws one bar per service, named by its host and value', () => {
    renderFigure()

    expect(screen.getByRole('img', { name: 'myhost: 40%' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'otherhost: 60%' })).toBeInTheDocument()
  })

  it('labels the bars with their hosts', () => {
    renderFigure()

    expect(screen.getByText('myhost')).toBeInTheDocument()
    expect(screen.getByText('otherhost')).toBeInTheDocument()
  })

  it('hides the host labels when the bars are too narrow for them', () => {
    renderFigure({}, { height: 40 })

    expect(screen.queryByText('myhost')).toBeNull()
  })

  it('labels the axis of a fixed range with the formatted ticks below its end', () => {
    renderFigure({ range: { minimum: 0, maximum: 100 } })

    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.queryByText('100%')).toBeNull()
  })

  it('wraps every bar in the contextual link trigger', () => {
    renderFigure()

    expect(screen.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      expect.stringContaining('host=myhost'),
      expect.stringContaining('host=otherhost')
    ])
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '300')
    expect(svg).toHaveAttribute('height', '200')
    expect(svg).toHaveAttribute('viewBox', '0 0 300 200')
  })
})
