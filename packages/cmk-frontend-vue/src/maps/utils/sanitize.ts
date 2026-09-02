/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import sanitizeHtml from 'sanitize-html'

// Single source for every URL sink fed by map data (template hrefs here,
// click navigation in mapNavigation.ts). Mirrors the backend allowlist in
// backend/app/schemas/_validators.py — keep the three in sync. The remote
// access schemes (ssh/rdp/…) are user-mediated OS handlers monitoring maps
// traditionally link on host objects; none of them is script-capable.
export const SAFE_URL_SCHEMES = [
  'http',
  'https',
  'mailto',
  'tel',
  'ssh',
  'telnet',
  'rdp',
  'vnc',
  'ftp'
]

// The remote access schemes are handed to a local OS handler that splits the URL
// into command arguments, so the scheme alone is not enough: a user or host
// starting with "-" arrives as an option (ssh://-oProxyCommand=…@host runs a
// command), whitespace or a percent escape hides one argument inside another.
// Mirrors _validate_os_handler_authority in cmk/maps/shared/validators.py.
const OS_HANDLER_SCHEMES = ['ssh:', 'telnet:', 'rdp:', 'vnc:']

export function hasSafeUrlAuthority(url: string): boolean {
  const scheme = url.slice(0, url.indexOf(':') + 1).toLowerCase()
  if (!OS_HANDLER_SCHEMES.includes(scheme)) {
    return true
  }
  const authority = url.slice(scheme.length).replace(/^\/\//, '').split(/[/?#]/)[0] ?? ''
  const at = authority.lastIndexOf('@')
  const userinfo = at < 0 ? '' : authority.slice(0, at)
  const host = authority.slice(at + 1)
  return (
    host !== '' && !userinfo.startsWith('-') && !host.startsWith('-') && !/[\s%]/.test(authority)
  )
}

// Allowlist for user-defined hover/context templates. Interpolated monitoring
// data (plugin output, host names) must never become a script vector. Beyond
// the former DOMPurify set this covers table layouts and inline icons, which
// imported NagVis templates conventionally use. Inline styles are limited to
// cosmetic properties; that alone does NOT keep a template inside its card —
// margins and sizes reach far outside it, so the paint containment on the
// template containers is what blocks an overlay.
// url(...) is rejected to prevent exfiltration pings on render, in the escaped
// and commented spellings a browser still reads as one too.
const SAFE_STYLE_VALUE = [/^(?!.*(?:url\s*\(|\\|\/\*))[^;{}]*$/i]

const TEMPLATE_SANITIZE_OPTIONS: sanitizeHtml.IOptions = {
  allowedTags: [
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
  allowedAttributes: {
    '*': ['href', 'class', 'style'],
    // target/rel only on <a>, and forced to safe values via transformTags.
    a: ['href', 'class', 'style', 'target', 'rel'],
    img: ['src', 'alt', 'width', 'height', 'class', 'style']
  },
  // Author templates can be published to other users, so links must not be able
  // to enable reverse tabnabbing (window.opener) or leak the referrer.
  // The scheme allowlist below cannot see the authority, so an href a remote
  // access handler would read as options is dropped here.
  transformTags: {
    a: (tagName, attribs) => {
      const hardened: sanitizeHtml.Attributes = {
        ...attribs,
        rel: 'noopener noreferrer nofollow',
        target: '_blank'
      }
      if (hardened.href !== undefined && !hasSafeUrlAuthority(hardened.href)) {
        delete hardened.href
      }
      return { tagName, attribs: hardened }
    }
  },
  // <img> may only load same-origin/relative URLs — an external src would be a
  // render-time exfiltration beacon (host/output + viewer IP) on every hover.
  // Protocol-relative URLs (//host/...) carry no scheme, so the scheme
  // allowlists alone would let them through.
  allowedSchemesByTag: { img: [] },
  allowProtocolRelative: false,
  allowedStyles: {
    '*': {
      color: SAFE_STYLE_VALUE,
      'background-color': SAFE_STYLE_VALUE,
      'font-size': SAFE_STYLE_VALUE,
      'font-weight': SAFE_STYLE_VALUE,
      'font-style': SAFE_STYLE_VALUE,
      'font-family': SAFE_STYLE_VALUE,
      'text-align': SAFE_STYLE_VALUE,
      'text-decoration': SAFE_STYLE_VALUE,
      'white-space': SAFE_STYLE_VALUE,
      padding: SAFE_STYLE_VALUE,
      'padding-top': SAFE_STYLE_VALUE,
      'padding-right': SAFE_STYLE_VALUE,
      'padding-bottom': SAFE_STYLE_VALUE,
      'padding-left': SAFE_STYLE_VALUE,
      margin: SAFE_STYLE_VALUE,
      'margin-top': SAFE_STYLE_VALUE,
      'margin-right': SAFE_STYLE_VALUE,
      'margin-bottom': SAFE_STYLE_VALUE,
      'margin-left': SAFE_STYLE_VALUE,
      border: SAFE_STYLE_VALUE,
      'border-radius': SAFE_STYLE_VALUE,
      width: SAFE_STYLE_VALUE,
      height: SAFE_STYLE_VALUE,
      'max-width': SAFE_STYLE_VALUE,
      'max-height': SAFE_STYLE_VALUE
    }
  },
  allowedSchemes: SAFE_URL_SCHEMES
}

export function sanitizeTemplateHtml(html: string): string {
  return sanitizeHtml(html, TEMPLATE_SANITIZE_OPTIONS)
}
