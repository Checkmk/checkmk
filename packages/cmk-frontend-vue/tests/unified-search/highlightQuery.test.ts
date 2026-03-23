/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { initSearchUtils } from '@/unified-search/providers/search-utils'

// All tests share the same module-level Vue refs via initSearchUtils. The
// beforeEach hook resets query.input.value before every test to keep them
// independent of each other.
describe('highlightQuery', () => {
  let utils: ReturnType<typeof initSearchUtils>

  beforeEach(() => {
    utils = initSearchUtils('test')
    utils.query.input.value = ''
  })

  // --- no query ---

  test('returns plain text unchanged when query is empty', () => {
    expect(utils.highlightQuery('my-host.example.com')).toBe('my-host.example.com')
  })

  test('returns empty string for empty input', () => {
    expect(utils.highlightQuery('')).toBe('')
  })

  test('whitespace-only query returns text without highlights', () => {
    utils.query.input.value = '   '
    expect(utils.highlightQuery('disk usage')).toBe('disk usage')
  })

  // --- highlighting ---

  test('wraps matching term in highlight span', () => {
    utils.query.input.value = 'disk'

    expect(utils.highlightQuery('disk usage on server')).toBe(
      '<span class="highlight-query">disk</span> usage on server'
    )
  })

  test('matching is case-insensitive', () => {
    utils.query.input.value = 'DISK'

    expect(utils.highlightQuery('disk usage on server')).toContain(
      '<span class="highlight-query">disk</span>'
    )
  })

  test('regex special characters in query are treated as literals', () => {
    utils.query.input.value = 'cpu (util)'

    expect(utils.highlightQuery('host cpu (util) check')).toContain(
      '<span class="highlight-query">cpu (util)</span>'
    )
  })

  // --- XSS: titles containing HTML must be escaped, match still highlighted ---

  test('HTML in title is escaped, matching term is still highlighted', () => {
    utils.query.input.value = 'cpu'

    const result = utils.highlightQuery('<img src=x onerror=alert(1)> cpu utilization')

    expect(result).not.toContain('<img')
    expect(result).toContain('&lt;img')
    expect(result).toContain('<span class="highlight-query">cpu</span>')
  })

  test('HTML payload matched by query is escaped inside the highlight span', () => {
    utils.query.input.value = 'alert'

    const result = utils.highlightQuery('<script>alert(1)</script>')

    expect(result).not.toContain('<script>')
    expect(result).toContain('<span class="highlight-query">alert</span>')
  })

  // --- entity integrity: query must not match inside escaped entities ---

  test('searching "amp" does not match inside &amp; entity', () => {
    utils.query.input.value = 'amp'

    const result = utils.highlightQuery('foo & bar')

    expect(result).not.toContain('&<span')
    expect(result).toContain('&amp;')
  })

  test('searching "&" highlights the & character as an HTML entity', () => {
    utils.query.input.value = '&'

    const result = utils.highlightQuery('foo & bar')

    expect(result).toContain('<span class="highlight-query">&amp;</span>')
  })

  // --- emoji safety ---

  test('emoji in title is preserved when highlighting a nearby term', () => {
    utils.query.input.value = 'host'

    expect(utils.highlightQuery('host 🎉 check')).toBe(
      '<span class="highlight-query">host</span> 🎉 check'
    )
  })
})
