/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  columnIdsFromVisibility,
  reconcile,
  visibilityFromColumnIds
} from '@/monitoring/shared/tableState/reconcile'
import type { RawTableState, TableStateSchema } from '@/monitoring/shared/tableState/types'

const schema: TableStateSchema = {
  hideable: ['alias', 'address', 'folder'],
  sortable: new Set(['name', 'state']),
  defaultVisibility: { alias: false },
  offeredLimits: [1000, 5000]
}

function raw(overrides: Partial<RawTableState> = {}): RawTableState {
  return { cols: undefined, sort: [], limit: undefined, ...overrides }
}

describe('reconcile - cols', () => {
  it('drops an unknown column and records a problem', () => {
    const { state, problems } = reconcile(raw({ cols: ['address', 'bogus'] }), schema)
    expect(state.cols).toEqual(['address'])
    expect(problems).toEqual([{ dimension: 'cols', message: expect.stringContaining('unknown') }])
  })

  it('falls back to unspecified when nothing in a non-empty list survives', () => {
    const { state } = reconcile(raw({ cols: ['bogus'] }), schema)
    expect(state.cols).toBeUndefined()
  })

  it('keeps an explicitly empty list as "hide everything", not unspecified', () => {
    const { state } = reconcile(raw({ cols: [] }), schema)
    expect(state.cols).toEqual([])
  })

  it('passes an unspecified param through unchanged', () => {
    const { state } = reconcile(raw({ cols: undefined }), schema)
    expect(state.cols).toBeUndefined()
  })
})

describe('reconcile - sort', () => {
  it('drops a column the API cannot sort', () => {
    const { state, problems } = reconcile(raw({ sort: [{ id: 'folder', desc: false }] }), schema)
    expect(state.sort).toEqual([])
    expect(problems).toHaveLength(1)
  })

  it('keeps a sort on a hidden column as-is - no coupling with cols in either direction', () => {
    const { state } = reconcile(
      raw({ cols: ['address'], sort: [{ id: 'name', desc: false }] }),
      schema
    )
    expect(state.cols).toEqual(['address'])
    expect(state.sort).toEqual([{ id: 'name', desc: false }])
  })

  it('keeps only the first occurrence of a repeated column', () => {
    const { state, problems } = reconcile(
      raw({
        sort: [
          { id: 'name', desc: false },
          { id: 'name', desc: true }
        ]
      }),
      schema
    )
    expect(state.sort).toEqual([{ id: 'name', desc: false }])
    expect(problems).toHaveLength(1)
  })
})

describe('reconcile - limit', () => {
  it('defaults when unspecified', () => {
    const { state, problems } = reconcile(raw({ limit: undefined }), schema)
    expect(state.limit).toBe(1000)
    expect(problems).toEqual([])
  })

  it('clamps "all" to the largest tier when the user may not remove the limit', () => {
    const { state, problems } = reconcile(raw({ limit: null }), schema)
    expect(state.limit).toBe(5000)
    expect(problems).toHaveLength(1)
  })

  it('honours "all" when the schema offers it', () => {
    const withUnlimited: TableStateSchema = { ...schema, offeredLimits: [1000, 5000, null] }
    const { state, problems } = reconcile(raw({ limit: null }), withUnlimited)
    expect(state.limit).toBeNull()
    expect(problems).toEqual([])
  })

  it('clamps a numeric value not in the offered tiers to the largest tier at or below it', () => {
    const { state } = reconcile(raw({ limit: 2000 }), schema)
    expect(state.limit).toBe(1000)
  })

  it('clamps a value below every tier up to the smallest tier', () => {
    const { state } = reconcile(raw({ limit: 10 }), schema)
    expect(state.limit).toBe(1000)
  })

  it('keeps a value that matches an offered tier exactly', () => {
    const { state, problems } = reconcile(raw({ limit: 5000 }), schema)
    expect(state.limit).toBe(5000)
    expect(problems).toEqual([])
  })

  it('falls back to the default tier for a legacy soft/hard/none-shaped token', () => {
    // Codecs decode an unparseable token (including legacy `soft`/`hard`/`none`) as `undefined`,
    // indistinguishable here from "absent" - both resolve to the default tier.
    const { state } = reconcile(raw({ limit: undefined }), schema)
    expect(state.limit).toBe(1000)
  })
})

describe('visibilityFromColumnIds / columnIdsFromVisibility', () => {
  it('round-trip through each other', () => {
    const visible = ['address']
    const visibility = visibilityFromColumnIds(visible, schema.hideable)
    expect(visibility).toEqual({ alias: false, address: true, folder: false })
    expect(columnIdsFromVisibility(visibility, schema.hideable)).toEqual(['address'])
  })

  it('marks every hideable column visible, explicitly, when all are named', () => {
    expect(visibilityFromColumnIds(schema.hideable, schema.hideable)).toEqual({
      alias: true,
      address: true,
      folder: true
    })
  })
})
