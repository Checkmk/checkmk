/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const QUERY_KIOSK = 'kiosk'

/** The values `cmk.web.utils.urls.is_truthy_query_value` accepts, which is what the
 * server reads to decide whether it renders the main navigation and sidebar. Every
 * other value, the empty one included, leaves the navigation in place - so reading
 * the parameter has to mean reading its value, not asking whether it is there. */
const TRUTHY_QUERY_VALUES = new Set(['1', 't', 'true', 'y', 'yes', 'on'])

function isTruthy(value: string | null): boolean {
  return value !== null && TRUTHY_QUERY_VALUES.has(value.trim().toLowerCase())
}

export const kioskMode = {
  /** Whether the kiosk query parameter asks for a page without the main navigation and
   * sidebar. A repeated parameter resolves to its last occurrence, the way the server's
   * `Request.var` reads it.
   * @returns A boolean indicating whether kiosk mode is active.
   */
  isActive(): boolean {
    const values = new URLSearchParams(window.location.search).getAll(QUERY_KIOSK)
    return isTruthy(values.at(-1) ?? null)
  },

  /** Derive a URL that opens with or without the main navigation and sidebar.
   * @param url - The URL to derive from.
   * @param kiosk - Whether the derived URL should hide navigation and sidebar.
   * @returns A new URL object; the input is left untouched.
   */
  withKiosk(url: URL, kiosk: boolean): URL {
    const result = new URL(url)
    if (kiosk) {
      result.searchParams.set(QUERY_KIOSK, 'true')
    } else {
      result.searchParams.delete(QUERY_KIOSK)
    }
    return result
  },

  /** Derive a URL that flips the current kiosk state, for links that toggle the main
   * navigation and sidebar.
   * @param url - The URL to derive from.
   * @returns A new URL object; the input is left untouched.
   */
  toggled(url: URL): URL {
    return kioskMode.withKiosk(url, !kioskMode.isActive())
  }
}
