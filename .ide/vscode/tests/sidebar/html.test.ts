/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { esc, getNonce, renderLoading, wrap } from '../../src/sidebar/html'

describe('esc', () => {
  it('escapes ampersands', () => {
    expect(esc('a & b')).toBe('a &amp; b')
  })

  it('escapes angle brackets', () => {
    expect(esc('<script>')).toBe('&lt;script&gt;')
  })

  it('escapes double quotes', () => {
    expect(esc('say "hello"')).toBe('say &quot;hello&quot;')
  })

  it('escapes all special chars together', () => {
    expect(esc('<a href="x">&')).toBe('&lt;a href=&quot;x&quot;&gt;&amp;')
  })

  it('coerces numbers to string', () => {
    expect(esc(42)).toBe('42')
  })

  it('coerces null to string', () => {
    expect(esc(null)).toBe('null')
  })

  it('coerces undefined to string', () => {
    expect(esc(undefined)).toBe('undefined')
  })

  it('handles empty string', () => {
    expect(esc('')).toBe('')
  })
})

describe('getNonce', () => {
  it('returns a 32-character hex string', () => {
    const nonce = getNonce()
    expect(nonce).toMatch(/^[0-9a-f]{32}$/)
  })

  it('returns unique values on successive calls', () => {
    const a = getNonce()
    const b = getNonce()
    expect(a).not.toBe(b)
  })
})

describe('wrap', () => {
  const nonce = 'abc123'

  it('produces a valid HTML document', () => {
    const html = wrap(nonce, '', '<p>body</p>')
    expect(html).toContain('<!DOCTYPE html>')
    expect(html).toContain('<html lang="en">')
    expect(html).toContain('</html>')
  })

  it('includes CSP meta tag with nonce', () => {
    const html = wrap(nonce, '', '')
    expect(html).toContain(`style-src 'nonce-${nonce}'`)
    expect(html).toContain(`script-src 'nonce-${nonce}'`)
  })

  it('includes the body content', () => {
    const html = wrap(nonce, '', '<div id="test">hello</div>')
    expect(html).toContain('<div id="test">hello</div>')
  })

  it('includes custom CSS in a nonce-tagged style element', () => {
    const html = wrap(nonce, '.custom { color: red; }', '')
    expect(html).toContain(`<style nonce="${nonce}">`)
    expect(html).toContain('.custom { color: red; }')
  })

  it('omits codicon font-face and font-src when codiconUri is not provided', () => {
    const html = wrap(nonce, '', '')
    expect(html).not.toContain("font-family: 'codicon'")
    expect(html).not.toContain('font-src')
  })

  it('includes codicon CSS and font-src when codiconUri is provided', () => {
    const html = wrap(nonce, '', '', 'https://ext/codicon.ttf', 'https://ext')
    expect(html).toContain("font-family: 'codicon'")
    expect(html).toContain('font-src https://ext;')
    expect(html).toContain('.codicon-terminal::before')
  })

  it('includes the acquireVsCodeApi script with nonce', () => {
    const html = wrap(nonce, '', '')
    expect(html).toContain(`<script nonce="${nonce}">`)
    expect(html).toContain('acquireVsCodeApi()')
  })
})

describe('renderLoading', () => {
  it('returns HTML with a loading spinner', () => {
    const html = renderLoading()
    expect(html).toContain('Refreshing')
    expect(html).toContain('<!DOCTYPE html>')
  })

  it('contains a spin animation', () => {
    const html = renderLoading()
    expect(html).toContain('@keyframes spin')
  })
})
