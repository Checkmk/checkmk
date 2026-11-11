/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  ACTIVE_MARKUP,
  BOUNDARY_MARKUP,
  type SurfacePolicy,
  activeContentIn,
  inertVHtmlContent
} from 'cmk-ui-library/vitest.sanitize'
import { describe, expect, it } from 'vitest'

import { sanitizeTemplateHtml } from '@/maps/utils/sanitize'

const TEMPLATE: SurfacePolicy = {
  tags: [
    'b',
    'i',
    'u',
    'em',
    'strong',
    'span',
    'div',
    'p',
    'br',
    'hr',
    'a',
    'ul',
    'ol',
    'li',
    'code',
    'img',
    'table',
    'thead',
    'tbody',
    'tr',
    'td',
    'th'
  ],
  attributes: ['href', 'src', 'class', 'style', 'target', 'rel', 'alt', 'width', 'height'],
  classes: 'any',
  protocols: ['http:', 'https:', 'mailto:', 'tel:'],
  // Mirrors the backend's scheme allowlist, which stored maps are validated against on load.
  osHandlerProtocols: ['ftp:', 'ssh:', 'telnet:', 'rdp:', 'vnc:'],
  sameOriginImageSources: true
}

describe('sanitizeTemplateHtml', () => {
  it.each(ACTIVE_MARKUP)('renders %s as inert', (markup) => {
    const sanitized = inertVHtmlContent(sanitizeTemplateHtml(markup))

    expect(activeContentIn(sanitized, TEMPLATE)).toEqual([])
  })

  it.each(BOUNDARY_MARKUP)('keeps %s within the template policy, showing %s', (markup, text) => {
    const sanitized = inertVHtmlContent(sanitizeTemplateHtml(markup))

    expect(activeContentIn(sanitized, TEMPLATE)).toEqual([])
    expect(sanitized.textContent).toBe(text)
  })

  it.each(['/icons/host.png', 'host.svg'])(
    'keeps the same-origin icon %s within the template policy',
    (src) => {
      const sanitized = inertVHtmlContent(sanitizeTemplateHtml(`<img src="${src}" alt="host">`))

      expect(sanitized.querySelector('img')?.getAttribute('src')).toBe(src)
      expect(activeContentIn(sanitized, TEMPLATE)).toEqual([])
    }
  )

  it('keeps allowed markup', () => {
    const html = '<b>bold</b> <span class="x" style="color:red">red</span><br><ul><li>a</li></ul>'
    expect(sanitizeTemplateHtml(html)).toBe(
      '<b>bold</b> <span class="x" style="color:red">red</span><br /><ul><li>a</li></ul>'
    )
  })

  it('keeps table layouts and relative images but strips external image sources', () => {
    expect(sanitizeTemplateHtml('<table><tbody><tr><td>cell</td></tr></tbody></table>')).toBe(
      '<table><tbody><tr><td>cell</td></tr></tbody></table>'
    )
    // Relative/same-origin icons (the NagVis template convention) are kept.
    expect(sanitizeTemplateHtml('<img src="/icons/host.png" alt="x" />')).toBe(
      '<img src="/icons/host.png" alt="x" />'
    )
    // An external src is stripped: it would be a render-time exfiltration beacon
    // (host/output + viewer IP) on every hover (allowedSchemesByTag.img: []).
    expect(sanitizeTemplateHtml('<img src="https://example.com/icon.png" alt="x" />')).toBe(
      '<img alt="x" />'
    )
    // A protocol-relative src is external too, but carries no scheme — it must
    // be caught by allowProtocolRelative: false, not the scheme allowlist.
    expect(sanitizeTemplateHtml('<img src="//example.com/icon.png" alt="x" />')).toBe(
      '<img alt="x" />'
    )
    expect(sanitizeTemplateHtml('<a href="//example.com">x</a>')).toBe(
      '<a rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
  })

  it('keeps safe-scheme links and hardens them against tabnabbing/referrer leaks', () => {
    // Every link is forced to target=_blank + rel=noopener/noreferrer/nofollow,
    // since author templates can be published to other users.
    expect(sanitizeTemplateHtml('<a href="https://example.com" target="_blank">x</a>')).toBe(
      '<a href="https://example.com" target="_blank" rel="noopener noreferrer nofollow">x</a>'
    )
    // No pre-existing target -> the transform adds rel before target.
    expect(sanitizeTemplateHtml('<a href="mailto:a@b.c">x</a>')).toBe(
      '<a href="mailto:a@b.c" rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
    expect(sanitizeTemplateHtml('<a href="tel:+4912345">x</a>')).toBe(
      '<a href="tel:+4912345" rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
  })

  it('drops remote-access links whose authority reads as handler arguments', () => {
    // ssh://-oProxyCommand=…@host would reach the local handler as an option.
    expect(sanitizeTemplateHtml('<a href="ssh://-oProxyCommand=curl+evil@switch01">x</a>')).toBe(
      '<a rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
    expect(sanitizeTemplateHtml('<a href="vnc://kvm01%20-evil">x</a>')).toBe(
      '<a rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
    // A browser strips leading control/space and tab/newline in the scheme
    // before it parses, so these read as "ssh:" and launch the OS handler; the
    // authority check must see the same normalized form and drop them.
    expect(sanitizeTemplateHtml('<a href=" ssh://-oProxyCommand=curl+evil@switch01">x</a>')).toBe(
      '<a rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
    expect(
      sanitizeTemplateHtml('<a href="s&#9;sh://-oProxyCommand=curl+evil@switch01">x</a>')
    ).toBe('<a rel="noopener noreferrer nofollow" target="_blank">x</a>')
    // An ordinary remote-access link is untouched.
    expect(sanitizeTemplateHtml('<a href="ssh://ops@switch01:2222">x</a>')).toBe(
      '<a href="ssh://ops@switch01:2222" rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
  })

  it('drops remote-access links that are more than user, host and port', () => {
    for (const href of [
      'ssh://switch01:-oProxyCommand=x',
      'ssh:\\\\-oProxyCommand=x',
      'rdp://ops@h\\x'
    ]) {
      expect(sanitizeTemplateHtml(`<a href="${href}">x</a>`)).toBe(
        '<a rel="noopener noreferrer nofollow" target="_blank">x</a>'
      )
    }
    expect(sanitizeTemplateHtml('<a href="ssh://ops@switch01:2222/-not-an-option">x</a>')).toBe(
      '<a href="ssh://ops@switch01:2222/-not-an-option" rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
  })

  it('keeps only image sources that name an image file', () => {
    for (const src of [
      'logout.py',
      '/heute/check_mk/logout.py',
      '/x.png?a=1',
      './logout.py#.png'
    ]) {
      expect(sanitizeTemplateHtml(`<img src="${src}" alt="x" />`)).toBe('<img alt="x" />')
    }
    expect(sanitizeTemplateHtml('<img src="host.svg" alt="x" />')).toBe(
      '<img src="host.svg" alt="x" />'
    )
  })

  it('blocks overlay/positioning styles but keeps cosmetic ones', () => {
    expect(
      sanitizeTemplateHtml('<div style="position:fixed;inset:0;z-index:9999;color:red">x</div>')
    ).toBe('<div style="color:red">x</div>')
    expect(sanitizeTemplateHtml('<span style="opacity:0">x</span>')).toBe('<span>x</span>')
  })

  it('blocks url() values in styles (exfiltration ping)', () => {
    expect(
      sanitizeTemplateHtml('<div style="background-color:url(https://evil.example)">x</div>')
    ).toBe('<div>x</div>')
    // A CSS escape or a comment between name and paren still reads as url() in
    // the browser, so the spelling alone must not get a value through.
    expect(
      sanitizeTemplateHtml('<div style="background-color:\\75 rl(https://evil.example)">x</div>')
    ).toBe('<div>x</div>')
    expect(
      sanitizeTemplateHtml('<div style="background-color:url/**/(https://evil.example)">x</div>')
    ).toBe('<div>x</div>')
    expect(
      sanitizeTemplateHtml('<div style="background-color:red\nurl(https://evil.example)">x</div>')
    ).toBe('<div>x</div>')
    // Values that legitimately carry parens or a minus stay allowed.
    expect(sanitizeTemplateHtml('<div style="color:rgb(1, 2, 3);margin:-4px">x</div>')).toBe(
      '<div style="color:rgb(1, 2, 3);margin:-4px">x</div>'
    )
  })

  it('drops disallowed tags but keeps their text content', () => {
    expect(sanitizeTemplateHtml('<button>t</button><form>f</form>')).toBe('tf')
  })
})
