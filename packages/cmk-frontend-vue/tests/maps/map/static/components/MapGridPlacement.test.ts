/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapGridPlacement from '@/maps/map/static/components/MapGridPlacement.vue'

import { anObject } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

describe('MapGridPlacement', () => {
  it('frames a full row of the grid, and says how many objects it holds', () => {
    const grid = anObject({ id: 'g', type: 'grid', grid_per_row: 4, grid_offset_x: 50 })

    const { container } = render(MapGridPlacement, {
      props: { grid, iconSize: 30, boxStyle: {} },
      global: mapsGlobal()
    })

    expect(screen.getByText('4 per row')).toBeInTheDocument()
    // Three gaps between four icons.
    const frame = container.querySelector<HTMLElement>('.maps-map-grid-placement__frame')!
    expect(frame.style.width).toBe('calc(180px + 2 * var(--dimension-4))')
  })
})
