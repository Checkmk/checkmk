/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { reconcile } from '@/monitoring/shared/filterState/reconcile'
import type { FilterUrlSchema, RawFilterUrlState } from '@/monitoring/shared/filterState/types'

const schema: FilterUrlSchema = {
  filterableFields: new Set(['name', 'state'])
}

function raw(overrides: Partial<RawFilterUrlState> = {}): RawFilterUrlState {
  return { filter: undefined, search: '', ...overrides }
}

describe('reconcile - filter', () => {
  it('passes through a well-formed condition on a known field', () => {
    const condition = { type: 'condition', field: 'name', op: 'contains', value: 'web' }
    const { state, problems } = reconcile(raw({ filter: condition }), schema)
    expect(state.filter).toEqual(condition)
    expect(problems).toEqual([])
  })

  it('drops a condition on an unknown field and records a problem', () => {
    const { state, problems } = reconcile(
      raw({ filter: { type: 'condition', field: 'bogus', op: 'eq', value: 'x' } }),
      schema
    )
    expect(state.filter).toBeUndefined()
    expect(problems).toHaveLength(1)
  })

  it('drops an unknown field from an and-group but keeps the rest', () => {
    const { state } = reconcile(
      raw({
        filter: {
          type: 'and',
          children: [
            { type: 'condition', field: 'name', op: 'contains', value: 'web' },
            { type: 'condition', field: 'bogus', op: 'eq', value: 'x' }
          ]
        }
      }),
      schema
    )
    expect(state.filter).toEqual({ type: 'condition', field: 'name', op: 'contains', value: 'web' })
  })

  it('drops the whole and-group when nothing in it survives', () => {
    const { state } = reconcile(
      raw({
        filter: {
          type: 'and',
          children: [{ type: 'condition', field: 'bogus', op: 'eq', value: 'x' }]
        }
      }),
      schema
    )
    expect(state.filter).toBeUndefined()
  })

  it('never throws on a garbage shape', () => {
    expect(() => reconcile(raw({ filter: 'not an object' }), schema)).not.toThrow()
    expect(() =>
      reconcile(raw({ filter: { type: 'and', children: 'nope' } }), schema)
    ).not.toThrow()
    expect(() => reconcile(raw({ filter: null }), schema)).not.toThrow()
    expect(() => reconcile(raw({ filter: [1, 2, 3] }), schema)).not.toThrow()
  })

  it('passes an unspecified filter through unchanged, with no problem', () => {
    const { state, problems } = reconcile(raw({ filter: undefined }), schema)
    expect(state.filter).toBeUndefined()
    expect(problems).toEqual([])
  })
})

describe('reconcile - search', () => {
  it('leaves ordinary text untouched', () => {
    const { state, problems } = reconcile(raw({ search: 'web01' }), schema)
    expect(state.search).toBe('web01')
    expect(problems).toEqual([])
  })

  it('strips control characters', () => {
    const { state, problems } = reconcile(raw({ search: 'we\u0000b\u001f01' }), schema)
    expect(state.search).toBe('web01')
    expect(problems).toHaveLength(1)
  })

  it('caps an excessively long search string', () => {
    const long = 'a'.repeat(400)
    const { state } = reconcile(raw({ search: long }), schema)
    expect(state.search).toHaveLength(300)
  })

  it('caps on the character the cap lands on rather than splitting it', () => {
    const { state } = reconcile(raw({ search: '\u{1f600}'.repeat(400) }), schema)
    expect(Array.from(state.search)).toHaveLength(300)
    expect(() => encodeURIComponent(state.search)).not.toThrow()
  })
})
