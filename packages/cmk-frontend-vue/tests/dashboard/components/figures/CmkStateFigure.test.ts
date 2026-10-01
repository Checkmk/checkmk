/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CmkStateFigure from '@/dashboard/components/figures/CmkStateFigure.vue'
import type { ObjectState } from '@/dashboard/types/widget'

const SERVICE_STATE: ObjectState = {
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
  state: 'CRITICAL',
  has_been_checked: true,
  tint_background: false,
  plugin_output: null
}

function renderFigure(value: Partial<ObjectState> = {}, interactive = true) {
  return render(CmkStateFigure, {
    props: {
      value: { ...SERVICE_STATE, ...value },
      width: 300,
      height: 200,
      filters: {},
      interactive
    }
  })
}

describe('CmkStateFigure', () => {
  it('draws the short name of the state', () => {
    renderFigure()

    expect(screen.getByText('CRIT')).toBeInTheDocument()
  })

  it('draws the short name of a host state', () => {
    renderFigure({ state: 'UNREACHABLE' })

    expect(screen.getByText('UNREACH')).toBeInTheDocument()
  })

  it('draws an unchecked object as pending', () => {
    renderFigure({ state: 'OK', has_been_checked: false })

    expect(screen.getByText('PEND')).toBeInTheDocument()
  })

  it('draws the plugin output when the server sends one', () => {
    renderFigure({ plugin_output: 'load is too high' })

    expect(screen.getByText('load is too high')).toBeInTheDocument()
  })

  it('wraps the state and the plugin output in the contextual link trigger', () => {
    renderFigure({ plugin_output: 'load is too high' })

    const link = screen.getByRole('link')
    expect(link).toHaveTextContent('CRIT')
    expect(link).toHaveTextContent('load is too high')
  })

  it('renders no anchor when not interactive', () => {
    renderFigure({}, false)

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
