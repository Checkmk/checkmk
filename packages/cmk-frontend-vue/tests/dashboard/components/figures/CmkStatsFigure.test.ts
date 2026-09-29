/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

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

const TABLE_BOX = { x: -20, y: 0, width: 100, height: 100 }
const HEXAGON_WIDTH = 48 * Math.sqrt(3)
const GROUP_GAP = 12

function renderFigure(interactive = true, width = 400) {
  return render(CmkStatsFigure, {
    props: { value: HOST_STATS, width, height: 200, filters: {}, interactive }
  })
}

function translateX(element: Element | null): number {
  const match = /translate\(([-\d.]+),/.exec(element?.getAttribute('transform') ?? '')
  return Number(match?.[1])
}

function hexagonX(): number {
  return translateX(screen.getAllByRole('img')[0]!.closest('g'))
}

function tableX(): number {
  return translateX(screen.getByRole('link', { name: /Total/ }).closest('g'))
}

describe('CmkStatsFigure', () => {
  beforeEach(() => {
    Object.defineProperty(SVGElement.prototype, 'getBBox', {
      configurable: true,
      value: () => TABLE_BOX
    })
  })

  afterEach(() => {
    Reflect.deleteProperty(SVGElement.prototype, 'getBBox')
  })

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

  it('centres the hexagon and the measured table as one group', async () => {
    renderFigure(true, 400)
    await nextTick()

    const groupX = (400 - (HEXAGON_WIDTH + GROUP_GAP + TABLE_BOX.width)) / 2
    expect(hexagonX()).toBeCloseTo(groupX + HEXAGON_WIDTH / 2)
    expect(tableX()).toBeCloseTo(groupX + HEXAGON_WIDTH + GROUP_GAP - TABLE_BOX.x)
  })

  it('aligns the group to the left edge when it does not fit', async () => {
    renderFigure(true, 150)
    await nextTick()

    expect(hexagonX()).toBeCloseTo(HEXAGON_WIDTH / 2)
    expect(tableX()).toBeCloseTo(HEXAGON_WIDTH + GROUP_GAP - TABLE_BOX.x)
  })
})
