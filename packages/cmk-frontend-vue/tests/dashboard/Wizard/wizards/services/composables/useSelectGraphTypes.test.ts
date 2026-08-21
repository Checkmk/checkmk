/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { ElementSelection } from '@/dashboard/components/Wizard/types'
import {
  Graph,
  getAvailableGraphs,
  getDisabledTooltip
} from '@/dashboard/components/Wizard/wizards/services/composables/useSelectGraphTypes'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

describe('getAvailableGraphs', () => {
  it('offers the service state only for a single host and a single service', () => {
    expect(
      getAvailableGraphs(
        ElementSelection.SPECIFIC,
        ElementSelection.SPECIFIC,
        DashboardFeatures.UNRESTRICTED
      )
    ).toContain(Graph.SERVICE_STATE)

    expect(
      getAvailableGraphs(
        ElementSelection.MULTIPLE,
        ElementSelection.SPECIFIC,
        DashboardFeatures.UNRESTRICTED
      )
    ).not.toContain(Graph.SERVICE_STATE)

    expect(
      getAvailableGraphs(
        ElementSelection.SPECIFIC,
        ElementSelection.MULTIPLE,
        DashboardFeatures.UNRESTRICTED
      )
    ).not.toContain(Graph.SERVICE_STATE)
  })
})

describe('getDisabledTooltip', () => {
  it('names the data selection when the edition is not the limiting factor', () => {
    expect(getDisabledTooltip(DashboardFeatures.UNRESTRICTED)).toBe(
      'Only available for a single host and a single service.'
    )
  })

  it('names the edition on a restricted edition', () => {
    expect(getDisabledTooltip(DashboardFeatures.RESTRICTED)).toBe(
      'Available in Checkmk Pro or higher.'
    )
  })
})
