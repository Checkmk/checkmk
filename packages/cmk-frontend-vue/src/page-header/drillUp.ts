/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** Where a drill-up leads: back in the tab's history, to the referring page, or nowhere. */
export type DrillUpTarget = 'history' | URL | null

/**
 * Back in the tab's history if it has one, else to the referrer, as in a tab the link opened.
 * Without either, the way back is lost. The referrer comes from outside, so only a page of this
 * site qualifies.
 */
export function drillUpTarget(
  historyLength: number,
  referrer: string,
  pageUrl: string
): DrillUpTarget {
  return historyLength > 1 ? 'history' : sameOriginUrl(referrer, pageUrl)
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
