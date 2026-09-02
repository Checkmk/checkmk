/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Where the SPA's own deployment lives, derived from the page it is served on.
 *
 * The Maps page is a normal GUI page (``/<site>/check_mk/maps.py``), and the
 * daemon and the map assets are proxied next to it under ``maps/`` — so a URL
 * resolved against the current document lands on the right site without the page
 * having to tell the SPA where it is. That mirrors the server side, which builds
 * the same paths from the request, and it is the same relative resolution
 * ``lib/rest-api-client`` uses for the REST API.
 */

/**
 * Base the daemon is proxied under, absolute (openapi-fetch needs a parseable
 * URL). The generated paths carry the ``/api/v1`` prefix themselves.
 */
export function resolveDaemonBase(): string {
  return new URL('maps', window.location.href).href
}

/**
 * Base for statically served Maps assets (uploaded images, map backgrounds —
 * GUI-owned, served by Apache under the site), with a trailing slash so callers
 * can append ``images/<name>``.
 */
export function resolveAssetBase(): string {
  return new URL('maps/', window.location.href).href
}

/** URL of the daemon's event stream for one map, carrying the stream credential. */
export function resolveStreamUrl(mapName: string, streamToken: string): string {
  const url = new URL(`${resolveDaemonBase()}/api/v1/sse/maps/${encodeURIComponent(mapName)}`)
  url.searchParams.set('token', streamToken)
  return url.href
}

/**
 * The Checkmk GUI the SPA is served by, without a trailing slash — the base every
 * deep link into Checkmk is built from.
 *
 * Derived from the page rather than configured: a map's connection may name the
 * URL of the site it monitors, but a link to *this* Checkmk is simply where the
 * SPA already is.
 */
export function resolveCheckmkUrl(): string {
  return new URL('.', window.location.href).href.replace(/\/$/, '')
}
