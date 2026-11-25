/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/** Names the page a drill-down left; the leading underscore keeps it out of further GET pages. */
export const DRILLED_FROM_PARAM = '_drilled_from'

/** Where a drill-up leads: back in the tab's history, to the referring page, or nowhere. */
export type DrillUpTarget = 'history' | URL | null

/** The parameter in which the dashboard hands an embedded view's iframe its own URL. */
export const IFRAME_DASHBOARD_URL_PARAM = 'drill_down_source_url'

/**
 * Only a click on a page of this site leaves a referrer that qualifies; the referrer comes from
 * outside, so no other page does. With one, back in the tab's history if it has one, else to the
 * referrer, as in a tab the link opened. A pasted, typed or bookmarked link has none: whatever
 * history its tab has leads elsewhere, so it offers no way back.
 */
export function drillUpTarget(
  historyLength: number,
  referrer: string,
  pageUrl: string
): DrillUpTarget {
  if (sameOriginUrl(referrer, pageUrl) === null) {
    return null
  }
  return historyLength > 1 ? 'history' : referringPage(referrer, pageUrl)
}

// A column link of an embedded view has the view's iframe as its referrer, not the dashboard; the
// dashboard hands that iframe its own URL.
function referringPage(referrer: string, pageUrl: string): URL | null {
  const url = sameOriginUrl(referrer, pageUrl)
  if (url === null || !url.pathname.endsWith('/widget_iframe_view.py')) {
    return url
  }
  return sameOriginUrl(url.searchParams.get(IFRAME_DASHBOARD_URL_PARAM) ?? '', pageUrl)
}

// A relative URL resolves against the page, not the origin, so it stays within the site's path.
function sameOriginUrl(candidate: string, pageUrl: string): URL | null {
  if (!candidate) {
    return null
  }
  try {
    const url = new URL(candidate, pageUrl)
    return url.origin === new URL(pageUrl).origin ? url : null
  } catch {
    return null
  }
}
