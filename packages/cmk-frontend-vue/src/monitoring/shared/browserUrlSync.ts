/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Where a table's URL-sync writer reads the current address bar from and
 * writes updates to. Injectable so a writer never has to reach for
 * `window.location`/`window.history` itself - a test can supply a plain
 * stub instead of jsdom location/history mocking, and a context that must
 * not touch the host page's address bar - a dashboard widget iframe, say -
 * can supply its own sync instead of an on/off flag.
 */
export interface UrlSync {
  getCurrentUrl(): { pathname: string; search: string; hash: string }
  replaceUrl(url: string): void
}

/** Reads and replaces the real address bar via `window.location`/`window.history`. */
export const browserUrlSync: UrlSync = {
  getCurrentUrl: () => ({
    pathname: window.location.pathname,
    search: window.location.search,
    hash: window.location.hash
  }),
  replaceUrl: (url) => window.history.replaceState(window.history.state, '', url)
}
