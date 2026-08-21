/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import WidgetTiles from '@/dashboard/components/Wizard/components/WidgetSelection/WidgetTiles.vue'
import type { WidgetItemList } from '@/dashboard/components/Wizard/components/WidgetSelection/types'

const availableItems = [
  { id: 'service_state', label: 'Service state', icon: 'graph' },
  { id: 'service_stats', label: 'Service statistics', icon: 'single-metric' }
] as WidgetItemList

const tooltipOf = (label: string): string | null =>
  screen
    .getByRole('button', { name: label })
    .querySelector('.db-disabled-tooltip-wrapper')
    ?.getAttribute('title') ?? null

describe('WidgetTiles', () => {
  it('explains why a disabled tile cannot be chosen', () => {
    render(WidgetTiles, {
      props: {
        availableItems,
        enabledWidgets: ['service_stats'],
        disabledTooltip: 'Only available for a single host and a single service.'
      }
    })

    expect(tooltipOf('Service state')).toBe(
      'Only available for a single host and a single service.'
    )
  })

  it('does not explain anything on a tile that can be chosen', () => {
    render(WidgetTiles, {
      props: {
        availableItems,
        enabledWidgets: ['service_state', 'service_stats'],
        disabledTooltip: 'Only available for a single host and a single service.'
      }
    })

    expect(tooltipOf('Service state')).toBeNull()
  })
})
