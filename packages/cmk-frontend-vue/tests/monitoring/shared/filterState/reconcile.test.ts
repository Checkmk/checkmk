/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { reconcile } from '@/monitoring/shared/filterState/reconcile'
import type { FilterUrlSchema, RawFilterUrlState } from '@/monitoring/shared/filterState/types'

const schema: FilterUrlSchema = {
  filterableFields: new Set(['name', 'state', 'last_state_change']),
  ageFields: new Set(['last_state_change'])
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

  it('drops an unknown field from an and-group, keeps the rest and records a problem', () => {
    const { state, problems } = reconcile(
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
    expect(problems).toHaveLength(1)
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

  it('passes through a well-formed age bound on a known field', () => {
    const age = { type: 'age', field: 'last_state_change', op: 'younger_than', seconds: 60 }
    const { state, problems } = reconcile(raw({ filter: age }), schema)
    expect(state.filter).toEqual(age)
    expect(problems).toEqual([])
  })

  it('keeps an age bound combined with a condition', () => {
    const filter = {
      type: 'and',
      children: [
        { type: 'condition', field: 'name', op: 'contains', value: 'web' },
        { type: 'age', field: 'last_state_change', op: 'older_than', seconds: 3600 }
      ]
    }
    const { state, problems } = reconcile(raw({ filter }), schema)
    expect(state.filter).toEqual(filter)
    expect(problems).toEqual([])
  })

  it.each([
    ['an unknown field', { field: 'bogus', op: 'younger_than', seconds: 60 }],
    ['a field that is not a timestamp', { field: 'state', op: 'younger_than', seconds: 60 }],
    ['an unknown op', { field: 'last_state_change', op: 'gte', seconds: 60 }],
    ['negative seconds', { field: 'last_state_change', op: 'younger_than', seconds: -1 }],
    ['infinite seconds', { field: 'last_state_change', op: 'younger_than', seconds: Infinity }],
    ['non-numeric seconds', { field: 'last_state_change', op: 'younger_than', seconds: '60' }],
    ['missing seconds', { field: 'last_state_change', op: 'younger_than' }]
  ])('drops an age bound with %s and records a problem', (_label, fields) => {
    const { state, problems } = reconcile(raw({ filter: { type: 'age', ...fields } }), schema)
    expect(state.filter).toBeUndefined()
    expect(problems).toHaveLength(1)
  })

  it('drops a malformed age bound from an and-group, keeps the condition and records a problem', () => {
    const { state, problems } = reconcile(
      raw({
        filter: {
          type: 'and',
          children: [
            { type: 'condition', field: 'name', op: 'contains', value: 'web' },
            { type: 'age', field: 'last_state_change', op: 'younger_than', seconds: -1 }
          ]
        }
      }),
      schema
    )
    expect(state.filter).toEqual({ type: 'condition', field: 'name', op: 'contains', value: 'web' })
    expect(problems).toHaveLength(1)
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
