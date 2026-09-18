/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Return the CSRF token delivered by the page's `<meta name="cmk-csrf-token">`.
 *
 * The token is emitted server-side on authenticated pages (see
 * cmk.gui.htmllib.html.HTMLGenerator.set_csrf_token_meta). Throws if the tag is
 * absent, which signals a page that should carry a token but does not.
 */
export function getCsrfToken(): string {
  const token = document.head.querySelector('meta[name="cmk-csrf-token"]')?.getAttribute('content')
  if (token === null || token === undefined) {
    throw new Error('CSRF token meta tag (cmk-csrf-token) not found')
  }
  return token
}
