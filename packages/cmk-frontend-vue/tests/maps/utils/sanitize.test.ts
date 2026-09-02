/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { sanitizeTemplateHtml } from '@/maps/utils/sanitize'

describe('sanitizeTemplateHtml', () => {
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
    // An ordinary remote-access link is untouched.
    expect(sanitizeTemplateHtml('<a href="ssh://ops@switch01:2222">x</a>')).toBe(
      '<a href="ssh://ops@switch01:2222" rel="noopener noreferrer nofollow" target="_blank">x</a>'
    )
  })

  it('strips script tags entirely', () => {
    expect(sanitizeTemplateHtml('before<script>alert(1)</script>after')).toBe('beforeafter')
  })

  it('strips event handler attributes', () => {
    expect(sanitizeTemplateHtml('<b onclick="alert(1)">x</b>')).toBe('<b>x</b>')
    expect(sanitizeTemplateHtml('<span onmouseover="alert(1)">x</span>')).toBe('<span>x</span>')
    // onerror is stripped; the relative src survives (an external src would be
    // stripped too — see the image-sources test).
    expect(sanitizeTemplateHtml('<img src="/x.png" onerror="alert(1)" />')).toBe(
      '<img src="/x.png" />'
    )
  })

  it('drops javascript: URLs but keeps the hardened link tag', () => {
    // The unsafe href is dropped; the tag stays and still gets the forced
    // target/rel hardening from transformTags.
    expect(sanitizeTemplateHtml('<a href="javascript:alert(1)">x</a>')).toBe(
      '<a rel="noopener noreferrer nofollow" target="_blank">x</a>'
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
    // Values that legitimately carry parens or a minus stay allowed.
    expect(sanitizeTemplateHtml('<div style="color:rgb(1, 2, 3);margin:-4px">x</div>')).toBe(
      '<div style="color:rgb(1, 2, 3);margin:-4px">x</div>'
    )
  })

  it('drops disallowed tags but keeps their text content', () => {
    expect(sanitizeTemplateHtml('<button>t</button><form>f</form>')).toBe('tf')
  })
})
