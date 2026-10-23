/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DetailAggregationSection from '@/maps/map/detail/components/DetailAggregationSection.vue'
import type { AggregationSummary } from '@/maps/map/detail/composables/useAggregationDetail'

import { mapsGlobal } from '../../../support/services'

const VIEW_OPTIONS = [
  { value: 'summary', label: 'Summary (depth 2)' },
  { value: 'details', label: 'Details' }
]

function aSummary(): AggregationSummary {
  return {
    chips: [],
    worstPath: null,
    worstOutput: null,
    leaves: [],
    treeRows: [],
    treeChips: [],
    treeDepth: 2
  }
}

function renderSection(extraProps: Record<string, unknown> = {}) {
  return render(DetailAggregationSection, {
    props: {
      summary: aSummary(),
      chips: [],
      view: 'summary',
      viewOptions: VIEW_OPTIONS,
      canSwitchView: true,
      rows: [],
      multiHost: false,
      problemLeafCount: 0,
      canAcknowledge: false,
      stale: false,
      ...extraProps
    },
    global: mapsGlobal()
  })
}

describe('DetailAggregationSection – the view switch', () => {
  it('offers the caller’s views on one named control', async () => {
    const user = userEvent.setup()
    renderSection()

    // Named, so the two labels are not the only thing identifying it — the
    // drawer is 360px wide and the control carries no visible label of its own.
    const control = screen.getByRole('combobox', { name: 'Aggregation view' })
    // CmkDropdown resolves the selected option's label a tick after mount.
    await waitFor(() => expect(control).toHaveTextContent('Summary (depth 2)'))

    await user.click(control)

    expect(screen.getByRole('option', { name: 'Summary (depth 2)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Details' })).toBeInTheDocument()
  })

  it('reports the picked view to the caller', async () => {
    const user = userEvent.setup()
    const { emitted } = renderSection()

    await user.click(screen.getByRole('combobox', { name: 'Aggregation view' }))
    await user.click(screen.getByRole('option', { name: 'Details' }))

    expect(emitted()['update:view']).toEqual([['details']])
  })

  it('hides the switch when the object asks for no cut tree', () => {
    renderSection({ canSwitchView: false })

    expect(screen.queryByRole('combobox', { name: 'Aggregation view' })).not.toBeInTheDocument()
  })
})
