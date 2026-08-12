/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { flatFilterUrlCodec } from '@/monitoring/shared/filterState/codec'
import { reconcile } from '@/monitoring/shared/filterState/reconcile'
import type { FilterUrlSchema, FilterUrlState } from '@/monitoring/shared/filterState/types'

function params(search: string): URLSearchParams {
  return new URLSearchParams(search)
}

describe('flatFilterUrlCodec.encode', () => {
  it('omits both keys at their default: no filter, empty search', () => {
    const state: FilterUrlState = { filter: undefined, search: '' }
    expect(flatFilterUrlCodec.encode(state)).toEqual({ filter: null, q: null })
  })

  it('encodes a filter as JSON', () => {
    const filter = {
      type: 'condition' as const,
      field: 'name' as const,
      op: 'contains' as const,
      value: 'web'
    }
    const state: FilterUrlState = { filter, search: '' }
    expect(flatFilterUrlCodec.encode(state).filter).toBe(JSON.stringify(filter))
  })

  it('encodes non-empty search verbatim', () => {
    const state: FilterUrlState = { filter: undefined, search: 'web01' }
    expect(flatFilterUrlCodec.encode(state).q).toBe('web01')
  })
})

describe('flatFilterUrlCodec.decode', () => {
  it('round-trips a filter and search text', () => {
    const filter = { type: 'condition', field: 'name', op: 'contains', value: 'web' }
    const decoded = flatFilterUrlCodec.decode(
      params(`?filter=${encodeURIComponent(JSON.stringify(filter))}&q=web01`)
    )
    expect(decoded).toEqual({ filter, search: 'web01' })
  })

  it('treats an absent filter as undefined and an absent q as empty', () => {
    expect(flatFilterUrlCodec.decode(params(''))).toEqual({ filter: undefined, search: '' })
  })

  it('leaves malformed JSON as undefined for reconciliation to drop', () => {
    expect(flatFilterUrlCodec.decode(params('?filter=not-json')).filter).toBeUndefined()
  })
})

describe('round trip', () => {
  // The read path (decode -> reconcile) and the write path (encode) are separate
  // code paths - see the module doc on tableState/useUrlTableState.ts, which this
  // module mirrors. Re-encoding a state that already came out of encode() must
  // reproduce the identical output; otherwise the address bar would drift on
  // every load/write cycle.
  const schema: FilterUrlSchema = { filterableFields: new Set(['name']) }
  const filter = {
    type: 'condition' as const,
    field: 'name' as const,
    op: 'contains' as const,
    value: 'web'
  }
  const cases: [string, FilterUrlState][] = [
    ['both at their default', { filter: undefined, search: '' }],
    ['a filter only', { filter, search: '' }],
    ['applied search only', { filter: undefined, search: 'web01' }],
    ['both a filter and applied search', { filter, search: 'web01' }]
  ]

  it.each(cases)(
    'encode -> decode -> reconcile -> encode is a fixed point (%s)',
    (_label, state) => {
      const encoded = flatFilterUrlCodec.encode(state)
      const asParams = new URLSearchParams()
      for (const [key, value] of Object.entries(encoded)) {
        if (value !== null) {
          asParams.set(key, value)
        }
      }

      const decoded = flatFilterUrlCodec.decode(asParams)
      const { state: reconciled } = reconcile(decoded, schema)

      expect(flatFilterUrlCodec.encode(reconciled)).toEqual(encoded)
    }
  )
})
