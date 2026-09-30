/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkGaugeFigure from '@/dashboard/components/figures/CmkGaugeFigure.vue'
import type { Gauge } from '@/dashboard/types/widget'

const GAUGE: Gauge = {
  links: [
    {
      title: 'Service',
      location: { type: 'views', name: 'service' },
      include_context: false,
      include_time_range: false,
      show_filter_form: false
    }
  ],
  link_properties: {
    links: [
      {
        siteopt: { status: 'encoded', variables: { site: 'heute' } },
        host: { status: 'encoded', variables: { host: 'myhost' } },
        service: { status: 'encoded', variables: { service: 'CPU load' } }
      }
    ]
  },
  value: 42,
  unit_format: {
    notation: 'decimal',
    symbol: '%',
    precision: { type: 'auto', digits: 2 },
    convertible: false
  },
  range: { minimum: 0, maximum: 100 },
  samples: [],
  status: null
}

function samples(values: number[]): Gauge['samples'] {
  return values.map((value, index) => ({
    timestamp: new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString(),
    value
  }))
}

function valueText(text: string) {
  return (_content: string, element: Element | null) =>
    element?.tagName === 'text' && element.textContent?.trim() === text
}

function renderFigure(value: Partial<Gauge> = {}, interactive = true) {
  return render(CmkGaugeFigure, {
    props: { value: { ...GAUGE, ...value }, width: 300, height: 200, filters: {}, interactive }
  })
}

describe('CmkGaugeFigure', () => {
  it('draws the value with its unit and the ends of the range', () => {
    renderFigure()

    expect(screen.getByText(valueText('42%'))).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('draws no value without a current value', () => {
    renderFigure({ value: null })

    expect(screen.queryByText(valueText('42%'))).toBeNull()
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('wraps the value in the contextual link trigger', () => {
    renderFigure()

    expect(screen.getByRole('link')).toHaveTextContent('42%')
  })

  it('renders no anchor when not interactive', () => {
    renderFigure({}, false)

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('labels the status with the short state of the service', () => {
    renderFigure({ status: { state: 'WARNING', has_been_checked: true, tint_background: false } })

    expect(screen.getByText('Service: WARN')).toBeInTheDocument()
  })

  it('labels an unchecked service as pending', () => {
    renderFigure({ status: { state: 'OK', has_been_checked: false, tint_background: false } })

    expect(screen.getByText('Service: PEND')).toBeInTheDocument()
  })

  it('draws one histogram bin per filled share from eleven values on', () => {
    renderFigure({ samples: samples([1, 1, 1, 1, 1, 60, 60, 60, 60, 99]) })

    expect(screen.getAllByRole('img').map((bin) => bin.getAttribute('aria-label'))).toEqual([
      '45.5%: 0% – 2.5%',
      '9.09%: 40% – 42.5%',
      '36.4%: 60% – 62.5%',
      '9.09%: 97.5% – 100%'
    ])
  })

  it('shows the share of a histogram bin on hover', async () => {
    renderFigure({ samples: samples([1, 1, 1, 1, 1, 60, 60, 60, 60, 99]) })

    await fireEvent.pointerMove(screen.getByRole('img', { name: '45.5%: 0% – 2.5%' }))

    expect(await screen.findByText('45.5%: 0% – 2.5%', { ignore: 'path' })).toBeInTheDocument()
  })

  it('draws no histogram below eleven values', () => {
    renderFigure({ samples: samples([1, 1, 1, 1, 1, 60, 60, 60, 60]) })

    expect(screen.queryAllByRole('img')).toEqual([])
  })

  it('sizes its root SVG and view box from its props', () => {
    renderFigure()

    const svg = screen.getByRole('figure')
    expect(svg).toHaveAttribute('width', '300')
    expect(svg).toHaveAttribute('height', '200')
    expect(svg).toHaveAttribute('viewBox', '0 0 300 200')
  })
})
