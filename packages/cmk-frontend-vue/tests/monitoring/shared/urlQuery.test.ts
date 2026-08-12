/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { encodeQueryValue, mergeQuery, parseQuery } from '@/monitoring/shared/urlQuery'

describe('encodeQueryValue', () => {
  it('leaves ids, numbers and the , ; : separators untouched', () => {
    expect(encodeQueryValue('state:desc,name:asc')).toBe('state:desc,name:asc')
  })

  it('escapes space as %20', () => {
    expect(encodeQueryValue('o brien')).toBe('o%20brien')
  })

  it('escapes an apostrophe, unlike encodeURIComponent', () => {
    expect(encodeURIComponent("o'brien")).toBe("o'brien")
    expect(encodeQueryValue("o'brien")).toBe('o%27brien')
  })

  it('escapes angle brackets and the pipe', () => {
    expect(encodeQueryValue('<a|b>')).toBe('%3Ca%7Cb%3E')
  })

  it('escapes the remaining characters URL_CHAR_REGEX excludes', () => {
    expect(encodeQueryValue('{}"\\^')).toBe('%7B%7D%22%5C%5E')
  })

  it('percent-encodes non-ASCII characters as UTF-8', () => {
    expect(encodeQueryValue('café')).toBe('caf%C3%A9')
  })
})

describe('parseQuery', () => {
  it('splits a leading-? search string into segments, keeping raw text intact', () => {
    expect(parseQuery('?a=1&b=2').map((segment) => segment.raw)).toEqual(['a=1', 'b=2'])
  })

  it('accepts a search string without the leading ?', () => {
    expect(parseQuery('a=1&b=2').map((segment) => segment.raw)).toEqual(['a=1', 'b=2'])
  })

  it('returns nothing for an empty search string', () => {
    expect(parseQuery('')).toEqual([])
    expect(parseQuery('?')).toEqual([])
  })

  it('decodes the key even though the raw text is left untouched', () => {
    const segments = parseQuery('host%5Fname=v300')
    expect(segments.map((segment) => segment.key)).toEqual(['host_name'])
    expect(segments.map((segment) => segment.raw)).toEqual(['host%5Fname=v300'])
  })
})

describe('mergeQuery', () => {
  it('preserves unknown params, their values and their order', () => {
    const search = '?host=v300&neg_host=&host_last_check_from=1&foo=bar'
    const merged = mergeQuery(search, { cols: 'address,folder' })
    expect(merged).toBe('?host=v300&neg_host=&host_last_check_from=1&foo=bar&cols=address,folder')
  })

  it('removes an owned key whose new value is null', () => {
    expect(mergeQuery('?cols=address&foo=bar', { cols: null })).toBe('?foo=bar')
  })

  it('replaces an existing owned key rather than duplicating it', () => {
    expect(mergeQuery('?limit=1000', { limit: '5000' })).toBe('?limit=5000')
  })

  it('returns a bare string when nothing survives', () => {
    expect(mergeQuery('?limit=1000', { limit: null })).toBe('')
  })

  it('never touches params outside the owned set, even when it writes nothing', () => {
    expect(mergeQuery('?foo=bar', { cols: null, sort: null, limit: null })).toBe('?foo=bar')
  })

  it('encodes written values strictly, not with encodeURIComponent', () => {
    expect(mergeQuery('', { cols: "o'brien" })).toBe('?cols=o%27brien')
  })
})
