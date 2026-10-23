/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { toFormValidation } from '@/maps/utils/formValidation'

describe('toFormValidation', () => {
  it('returns null when detail is not an array', () => {
    expect(toFormValidation(undefined)).toBeNull()
    expect(toFormValidation('nope')).toBeNull()
    expect(toFormValidation({ detail: 'x' })).toBeNull()
  })

  it('returns null on an empty array', () => {
    expect(toFormValidation([])).toBeNull()
  })

  it('returns null when entries do not look like pydantic errors', () => {
    expect(toFormValidation([{ msg: 'no loc' }])).toBeNull()
    expect(toFormValidation([{ loc: ['body', 'x'] }])).toBeNull()
  })

  it('maps a pydantic error to a ValidationMessage and strips the body prefix', () => {
    const result = toFormValidation([{ loc: ['body', 'title'], msg: 'field required', input: 'x' }])
    expect(result).not.toBeNull()
    expect(result!.messages).toEqual([
      { location: ['title'], message: 'field required', replacement_value: 'x' }
    ])
    expect(result!.summary).toBe('title: field required')
  })

  it('strips the "Value error," wrapper pydantic adds around raised ValueErrors', () => {
    const result = toFormValidation([{ loc: ['body', 'name'], msg: 'Value error, bad name' }])
    expect(result!.messages[0]!.message).toBe('bad name')
    expect(result!.summary).toBe('name: bad name')
  })

  it('defaults replacement_value to null when input is absent', () => {
    const result = toFormValidation([{ loc: ['body', 'name'], msg: 'x' }])
    expect(result!.messages[0]!.replacement_value).toBeNull()
  })

  it('routes errors on unknown top-level fields to stray', () => {
    const known = new Set(['title'])
    const result = toFormValidation(
      [
        { loc: ['body', 'title'], msg: 'a' },
        { loc: ['body', 'secret'], msg: 'b' }
      ],
      known
    )
    expect(result!.messages.map((m) => m.location[0])).toEqual(['title'])
    expect(result!.stray.map((m) => m.location[0])).toEqual(['secret'])
  })

  it('treats every error as routable when knownFields is omitted', () => {
    const result = toFormValidation([
      { loc: ['body', 'a'], msg: 'x' },
      { loc: ['body', 'b'], msg: 'y' }
    ])
    expect(result!.messages).toHaveLength(2)
    expect(result!.stray).toHaveLength(0)
  })

  it('summarises with "value" when the location is only "body"', () => {
    const result = toFormValidation([{ loc: ['body'], msg: 'broken' }])
    expect(result!.summary).toBe('value: broken')
  })
})
