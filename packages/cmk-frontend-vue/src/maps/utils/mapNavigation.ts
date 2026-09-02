/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapElement } from '@/maps/types/api'

import { SAFE_URL_SCHEMES, hasSafeUrlAuthority } from './sanitize'

// Strip the trailing "/check_mk" segment (and trailing slash) from a stored
// Checkmk GUI URL, leaving the site base every deep link is built from.
//
// Every :href in the map UI is built on top of this, and unlike openUrl() a
// bound href has no scheme check of its own — so an unsafe base is dropped here
// rather than at each call site. The server rejects such a value on save
// (shared/validators.py); this covers configs that predate it.
export function stripCheckmkBase(checkmkUrl: string | null | undefined): string {
  if (!checkmkUrl) {
    return ''
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(checkmkUrl) && !isSafeUrl(checkmkUrl)) {
    console.warn(`stripCheckmkBase: blocked unsafe URL scheme: ${checkmkUrl}`)
    return ''
  }
  return checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '')
}

function _baseAndSite(
  checkmkUrl: string | null,
  siteOverride?: string | null
): { base: string; p: Record<string, string> } | null {
  const base = stripCheckmkBase(checkmkUrl)
  if (!base) {
    return null
  }
  // Don't fall back to the URL's path segment — on a central that would pin
  // the link to the central site id even for hosts on remotes.
  const p: Record<string, string> = {}
  if (siteOverride) {
    p.site = siteOverride
  }
  return { base, p }
}

// Wrap a relative Checkmk path in `index.py?start_url=…` so the landing page
// keeps Checkmk's chrome (sidebar, top-bar, breadcrumbs) instead of dropping
// the operator into a bare view. Bare view URLs are still useful inside an
// embedded iframe (no double chrome), but at the Maps layer "open in
// Checkmk" always means "open the real Checkmk page".
function _wrapInChrome(base: string, viewPath: string, viewParams: URLSearchParams): string {
  const inner = `${viewPath}?${viewParams}`
  const outer = new URLSearchParams({ start_url: inner })
  return `${base}/check_mk/index.py?${outer}`
}

// One Checkmk view deep link. ``chrome: true`` wraps it in
// index.py?start_url=… so the landing page keeps Checkmk's sidebar/topbar
// (see _wrapInChrome) — bare view URLs stay useful inside embedded iframes.
export function buildCheckmkViewUrl(
  checkmkUrl: string | null | undefined,
  viewName: string,
  params: Record<string, string> = {},
  opts: { site?: string | null; chrome?: boolean } = {}
): string | null {
  const base = stripCheckmkBase(checkmkUrl)
  if (!base) {
    return null
  }
  const p: Record<string, string> = { view_name: viewName, ...params }
  if (opts.site) {
    p.site = opts.site
  }
  const search = new URLSearchParams(p)
  return opts.chrome ? _wrapInChrome(base, 'view.py', search) : `${base}/check_mk/view.py?${search}`
}

export function buildCheckmkUrl(
  obj: MapElement,
  checkmkUrl: string | null,
  siteOverride?: string | null
): string | null {
  // Don't fall back to the URL's path segment for the site — on a central
  // that would pin the link to the central site id even for remote hosts.
  const opts = { site: siteOverride ?? null, chrome: true }
  if ((obj.type === 'host' || obj.type === 'line') && obj.host_name && !obj.service_description) {
    return buildCheckmkViewUrl(checkmkUrl, 'hoststatus', { host: obj.host_name }, opts)
  }
  if ((obj.type === 'service' || obj.type === 'line') && obj.host_name && obj.service_description) {
    return buildCheckmkViewUrl(
      checkmkUrl,
      'service',
      { host: obj.host_name, service: obj.service_description },
      opts
    )
  }
  if (obj.type === 'hostgroup' && obj.group_name) {
    return buildCheckmkViewUrl(checkmkUrl, 'hostgroup', { hostgroup: obj.group_name }, opts)
  }
  if (obj.type === 'servicegroup' && obj.group_name) {
    return buildCheckmkViewUrl(checkmkUrl, 'servicegroup', { servicegroup: obj.group_name }, opts)
  }
  if (obj.type === 'aggregation' && obj.aggregation_id) {
    return buildCheckmkViewUrl(
      checkmkUrl,
      'aggr_single',
      { aggr_name: obj.aggregation_id, po_aggr_expand: '1' },
      opts
    )
  }
  if (obj.type === 'site' && obj.host_name) {
    // Site root drills into the per-site host overview.
    return buildCheckmkViewUrl(checkmkUrl, 'allhosts', {}, { site: obj.host_name, chrome: true })
  }
  return null
}

/**
 * For object types where the live monitoring view (``buildCheckmkUrl``)
 * isn't where the operator's "edit this thing" intent leads, return the
 * configuration/setup URL.
 *
 * BI aggregations: when ``packId`` is supplied (resolved from the
 * AggregationInfo cache the EditPanel + Drawer already keep), deep-link
 * straight into the rules editor of that pack (``mode=bi_rules&pack=…``)
 * so the operator can immediately find + edit the aggregation. Falls
 * back to the BI packs overview (``mode=bi_packs``) when no pack id is
 * available — better than nothing, just one extra click.
 */
export function buildCheckmkSetupUrl(
  obj: MapElement,
  checkmkUrl: string | null,
  packId?: string | null,
  siteOverride?: string | null
): string | null {
  const r = _baseAndSite(checkmkUrl, siteOverride)
  if (!r) {
    return null
  }
  const { base, p } = r
  if (obj.type === 'aggregation') {
    if (packId) {
      p.mode = 'bi_rules'
      p.pack = packId
    } else {
      p.mode = 'bi_packs'
    }
    return _wrapInChrome(base, 'wato.py', new URLSearchParams(p))
  }
  return null
}

// Defense-in-depth mirror of the backend allowlist (shared/validators.py):
// map JSON predating the server-side check may still carry hostile URLs.
const SAFE_PROTOCOLS = SAFE_URL_SCHEMES.map((s) => `${s}:`)

function isSafeUrl(url: string): boolean {
  try {
    return (
      SAFE_PROTOCOLS.includes(new URL(url, window.location.href).protocol) &&
      hasSafeUrlAuthority(url)
    )
  } catch {
    return false
  }
}

// Uses a real <a> click so the browser doesn't treat it as a popup (important
// when Maps runs inside a Checkmk iframe — window.open gets popup-blocked).
export function openUrl(url: string, target: string): void {
  let protocol: string
  try {
    protocol = new URL(url, window.location.href).protocol
  } catch {
    console.warn(`openUrl: unparseable URL blocked: ${url}`)
    return
  }
  if (!SAFE_PROTOCOLS.includes(protocol)) {
    console.warn(`openUrl: blocked unsafe URL scheme: ${protocol}`)
    return
  }
  if (!hasSafeUrlAuthority(url)) {
    console.warn(`openUrl: blocked unsafe URL authority: ${url}`)
    return
  }
  const a = document.createElement('a')
  a.href = url
  a.target = target
  a.rel = 'noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// Checkmk's filter machinery takes a single "svc_state" / "host_state" filter
// whose individual st*/hst* checkboxes are interpreted as a bitmask. A box
// only counts as ON when its parameter is present and equals "on" — sending
// "off" or omitting it both mean "exclude this state". The whole filter is
// only honored when "_active" lists svcstate/hoststate alongside the host /
// site filter; without it the Setup-defined view defaults win.
export function svcStateOn(state: string): string {
  if (state === 'CRITICAL') {
    return 'st2'
  }
  if (state === 'WARNING') {
    return 'st1'
  }
  if (state === 'UNKNOWN') {
    return 'st3'
  }
  if (state === 'PENDING') {
    return 'stp'
  }
  return 'st0' // OK
}

export function hostStateOn(state: string): string {
  if (state === 'DOWN') {
    return 'hst1'
  }
  if (state === 'UNREACHABLE') {
    return 'hst2'
  }
  return 'hst0' // UP
}

// host_regex over more than this many members would push the view URL past
// Apache's ~8 KB request-line limit, so the pill stays non-clickable above it.
const _MAX_HOST_REGEX_MEMBERS = 90

/**
 * Checkmk view listing a host's (or site's) services filtered to one state —
 * the target of the clickable state pills/chips in HoverMenu and DetailDrawer.
 * Returns null outside a Checkmk deployment or for states the svcstate filter
 * can't express (PENDING maps to the filter's "stp" checkbox, so it's fine).
 */
export function buildServiceStateViewUrl(
  checkmkUrl: string | null,
  target: {
    host?: string | null | undefined
    site?: string | null | undefined
    hosts?: string[] | null | undefined
  },
  state: string
): string | null {
  if (!checkmkUrl) {
    return null
  }
  if (!['OK', 'WARNING', 'CRITICAL', 'UNKNOWN', 'PENDING'].includes(state)) {
    return null
  }
  const params: Record<string, string> = {
    filled_in: 'filter',
    _active: 'svcstate;host',
    [svcStateOn(state)]: 'on'
  }
  if (target.site) {
    params.site = target.site
    params._active = 'svcstate;site'
  } else if (target.host) {
    params.host = target.host
  } else if (target.hosts && target.hosts.length) {
    if (target.hosts.length > _MAX_HOST_REGEX_MEMBERS) {
      return null
    }
    const alt = target.hosts.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
    params.host_regex = `^(${alt})$`
    params._active = 'svcstate;hostregex'
  } else {
    return null
  }
  params.display_options = _VIEW_LINK_DISPLAY_OPTIONS
  return buildCheckmkViewUrl(checkmkUrl, 'allservices', params, { chrome: true })
}

// Lone lowercase "f" hides Checkmk's filter bar, keeps the rest of the chrome.
const _VIEW_LINK_DISPLAY_OPTIONS = 'f'

/**
 * What an object's ``services_summary`` counts. Host groups roll up member HOST
 * states into that field; everyone else counts services. (Host dyngroups carry
 * their host rollup separately in ``hosts_summary``.)
 */
export function summarySubject(obj: MapElement): 'hosts' | 'services' {
  return obj.type === 'hostgroup' ? 'hosts' : 'services'
}

/**
 * Checkmk allhosts view filtered to one host state over a member set — the
 * target of clickable HOST state pills/chips on dyngroups.
 */
export function buildHostStateViewUrl(
  checkmkUrl: string | null,
  hosts: string[],
  state: string
): string | null {
  if (!checkmkUrl) {
    return null
  }
  if (!['UP', 'DOWN', 'UNREACHABLE'].includes(state)) {
    return null
  }
  if (!hosts.length || hosts.length > _MAX_HOST_REGEX_MEMBERS) {
    return null
  }
  const alt = hosts.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  return buildCheckmkViewUrl(
    checkmkUrl,
    'allhosts',
    {
      filled_in: 'filter',
      _active: 'hoststate;hostregex',
      host_regex: `^(${alt})$`,
      [hostStateOn(state)]: 'on',
      display_options: _VIEW_LINK_DISPLAY_OPTIONS
    },
    { chrome: true }
  )
}
