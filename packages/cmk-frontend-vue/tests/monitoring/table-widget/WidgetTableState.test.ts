/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { WidgetTableState } from '@/monitoring/table-widget/WidgetTableState'

describe('WidgetTableState', () => {
  it('starts in the configured order', () => {
    const state = new WidgetTableState(['state:desc', 'name:asc'])

    expect(state.encodedSort()).toEqual(['state:desc', 'name:asc'])
  })

  it('takes the order the viewer picks', () => {
    const state = new WidgetTableState(['name:asc'])

    state.updateSort([{ id: 'state', desc: true }])

    expect(state.encodedSort()).toEqual(['state:desc'])
  })

  it('goes back to the configured order once the viewer clears the sort', () => {
    const state = new WidgetTableState(['name:asc'])
    state.updateSort([{ id: 'state', desc: true }])

    state.updateSort([])

    expect(state.encodedSort()).toEqual(['name:asc'])
  })

  it('drops the viewer order once the configured order changes', () => {
    const state = new WidgetTableState(['name:asc'])
    state.updateSort([{ id: 'state', desc: true }])

    state.reset(['state:asc'])

    expect(state.encodedSort()).toEqual(['state:asc'])
  })

  it('clears back to the newly configured order', () => {
    const state = new WidgetTableState(['name:asc'])
    state.reset(['state:asc'])

    state.updateSort([])

    expect(state.encodedSort()).toEqual(['state:asc'])
  })

  it.each([
    { token: 'name', description: 'no direction' },
    { token: 'name:up', description: 'an unknown direction' },
    { token: ':asc', description: 'no column' },
    { token: '', description: 'an empty token' }
  ])('ignores a configured token with $description', ({ token }) => {
    const state = new WidgetTableState([token, 'state:desc'])

    expect(state.encodedSort()).toEqual(['state:desc'])
  })
})
