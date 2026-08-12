/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { flatTableStateCodec } from '@/monitoring/shared/tableState/codec'
import { reconcile } from '@/monitoring/shared/tableState/reconcile'
import type { TableState, TableStateSchema } from '@/monitoring/shared/tableState/types'

const schema: TableStateSchema = {
  hideable: ['alias', 'address', 'folder'],
  sortable: new Set(['name', 'state']),
  defaultVisibility: { alias: false },
  offeredLimits: [1000, 5000]
}

function params(search: string): URLSearchParams {
  return new URLSearchParams(search)
}

describe('flatTableStateCodec.encode', () => {
  it('omits every dimension at its default', () => {
    const state: TableState = { cols: ['address', 'folder'], sort: [], limit: 1000 }
    expect(flatTableStateCodec.encode(state, schema)).toEqual({
      cols: null,
      sort: null,
      limit: null
    })
  })

  it('treats an unspecified cols the same as the default column set', () => {
    const state: TableState = { cols: undefined, sort: [], limit: 1000 }
    expect(flatTableStateCodec.encode(state, schema).cols).toBeNull()
  })

  it('encodes non-default columns as an ordered, comma-separated list', () => {
    const state: TableState = { cols: ['folder'], sort: [], limit: 1000 }
    expect(flatTableStateCodec.encode(state, schema).cols).toBe('folder')
  })

  it('encodes cols= explicitly when every hideable column is hidden', () => {
    const state: TableState = { cols: [], sort: [], limit: 1000 }
    expect(flatTableStateCodec.encode(state, schema).cols).toBe('')
  })

  it('encodes multi-column sort as an ordered column:direction list', () => {
    const state: TableState = {
      cols: undefined,
      sort: [
        { id: 'state', desc: true },
        { id: 'name', desc: false }
      ],
      limit: 1000
    }
    expect(flatTableStateCodec.encode(state, schema).sort).toBe('state:desc,name:asc')
  })

  it('encodes an unlimited request as "all"', () => {
    const state: TableState = { cols: undefined, sort: [], limit: null }
    expect(flatTableStateCodec.encode(state, schema).limit).toBe('all')
  })

  it('encodes a non-default numeric limit', () => {
    const state: TableState = { cols: undefined, sort: [], limit: 5000 }
    expect(flatTableStateCodec.encode(state, schema).limit).toBe('5000')
  })
})

describe('flatTableStateCodec.decode', () => {
  it('round-trips cols, sort and limit', () => {
    const decoded = flatTableStateCodec.decode(
      params('?cols=address,folder&sort=state:desc,name:asc&limit=5000')
    )
    expect(decoded).toEqual({
      cols: ['address', 'folder'],
      sort: [
        { id: 'state', desc: true },
        { id: 'name', desc: false }
      ],
      limit: 5000
    })
  })

  it('treats an absent cols as unspecified, distinct from an empty one', () => {
    expect(flatTableStateCodec.decode(params('')).cols).toBeUndefined()
    expect(flatTableStateCodec.decode(params('?cols=')).cols).toEqual([])
  })

  it('decodes limit=all', () => {
    expect(flatTableStateCodec.decode(params('?limit=all')).limit).toBeNull()
  })

  it('leaves an unparseable limit as undefined for reconciliation to default', () => {
    expect(flatTableStateCodec.decode(params('?limit=soft')).limit).toBeUndefined()
  })

  it('drops a malformed sort token rather than throwing', () => {
    expect(flatTableStateCodec.decode(params('?sort=host,name:sideways')).sort).toEqual([])
  })
})

describe('round trip', () => {
  // The read path (decode -> reconcile) and the write path (encode) are separate
  // code paths - see the module doc on useUrlTableState.ts. Re-encoding a state
  // that already came out of encode() must reproduce the identical output;
  // otherwise the address bar would drift on every load/write cycle. Each
  // state must be one `reconcile` would actually produce for its schema - a
  // limit the schema doesn't offer is `reconcileLimit`'s job to clamp, a
  // separate guarantee already covered in reconcile.test.ts, not a case for
  // the fixed point this test pins.
  const unlimitedSchema: TableStateSchema = { ...schema, offeredLimits: [1000, 5000, null] }
  const cases: [string, TableState, TableStateSchema][] = [
    [
      'every dimension at its default',
      { cols: ['address', 'folder'], sort: [], limit: 1000 },
      schema
    ],
    ['a non-default column list', { cols: ['folder'], sort: [], limit: 1000 }, schema],
    ['every hideable column hidden', { cols: [], sort: [], limit: 1000 }, schema],
    [
      'a multi-column sort',
      {
        cols: undefined,
        sort: [
          { id: 'state', desc: true },
          { id: 'name', desc: false }
        ],
        limit: 1000
      },
      schema
    ],
    ['a non-default numeric limit', { cols: undefined, sort: [], limit: 5000 }, schema],
    [
      'no limit, when the schema offers it',
      { cols: undefined, sort: [], limit: null },
      unlimitedSchema
    ]
  ]

  it.each(cases)(
    'encode -> decode -> reconcile -> encode is a fixed point (%s)',
    (_label, state, caseSchema) => {
      const encoded = flatTableStateCodec.encode(state, caseSchema)
      const asParams = new URLSearchParams()
      for (const [key, value] of Object.entries(encoded)) {
        if (value !== null) {
          asParams.set(key, value)
        }
      }

      const decoded = flatTableStateCodec.decode(asParams)
      const { state: reconciled } = reconcile(decoded, caseSchema)

      expect(flatTableStateCodec.encode(reconciled, caseSchema)).toEqual(encoded)
    }
  )
})
