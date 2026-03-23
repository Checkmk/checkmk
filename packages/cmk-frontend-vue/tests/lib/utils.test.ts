/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { escapeHtml } from '@/lib/utils'

describe('escapeHtml', () => {
  test('escapes &', () => {
    expect(escapeHtml('foo & bar')).toBe('foo &amp; bar')
  })

  test('escapes <', () => {
    expect(escapeHtml('<script>')).toBe('&lt;script&gt;')
  })

  test('escapes >', () => {
    expect(escapeHtml('a > b')).toBe('a &gt; b')
  })

  test('escapes double quotes', () => {
    expect(escapeHtml('"hello"')).toBe('&quot;hello&quot;')
  })

  test('escapes single quotes', () => {
    expect(escapeHtml("it's")).toBe('it&#39;s')
  })

  test('leaves plain text unchanged', () => {
    expect(escapeHtml('my-host.example.com')).toBe('my-host.example.com')
  })

  test('returns empty string for empty input', () => {
    expect(escapeHtml('')).toBe('')
  })

  test('preserves emoji', () => {
    expect(escapeHtml('host 🎉 check')).toBe('host 🎉 check')
  })

  test('escapes multiple special characters in one string', () => {
    expect(escapeHtml('<img src=x onerror=alert(1)>')).toBe('&lt;img src=x onerror=alert(1)&gt;')
  })
})
