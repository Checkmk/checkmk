/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { ElementSelection } from '@/dashboard/components/Wizard/types'
import {
  getAvailableGraphs,
  getDisabledTooltip
} from '@/dashboard/components/Wizard/wizards/hosts-site/composables/useSelectGraphTypes'
import { Graph } from '@/dashboard/components/Wizard/wizards/hosts-site/types'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

describe('getAvailableGraphs', () => {
  it('offers the host state only for a single host', () => {
    expect(getAvailableGraphs(ElementSelection.SPECIFIC, DashboardFeatures.UNRESTRICTED)).toContain(
      Graph.HOST_STATE
    )

    expect(
      getAvailableGraphs(ElementSelection.MULTIPLE, DashboardFeatures.UNRESTRICTED)
    ).not.toContain(Graph.HOST_STATE)
  })
})

describe('getDisabledTooltip', () => {
  it('names the data selection when the edition is not the limiting factor', () => {
    expect(getDisabledTooltip(DashboardFeatures.UNRESTRICTED)).toBe(
      'Only available for a single host.'
    )
  })

  it('names the edition on a restricted edition', () => {
    expect(getDisabledTooltip(DashboardFeatures.RESTRICTED)).toBe(
      'Available in Checkmk Pro or higher.'
    )
  })
})
