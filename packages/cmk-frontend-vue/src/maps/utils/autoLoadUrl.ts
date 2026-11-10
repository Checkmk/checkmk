/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { assetUrl } from '@/maps/utils/assetUrl'

// Read-only pages a graph object may embed from the site itself.
// Mirrors _EMBEDDABLE_SITE_PAGES in cmk/maps/shared/validators.py.
const EMBEDDABLE_SITE_PAGES = new Set(['graph_image.py', 'view.py', 'dashboard.py'])

/**
 * Whether the map may load *url* by itself, with the viewer's session, as soon as
 * it is shown. A URL of this site is allowed only under the Maps image and
 * background directories, or when ``allowSitePath`` accepts its path.
 */
export function isAutoLoadable(
  url: string,
  allowSitePath: (path: string) => boolean = () => false
): boolean {
  let parsed: URL
  try {
    parsed = new URL(url, window.location.href)
  } catch {
    return false
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return false
  }
  // The session belongs to the host, whatever the scheme and port.
  if (parsed.hostname !== window.location.hostname) {
    return true
  }
  return (
    ['images/', 'backgrounds/'].some((dir) =>
      parsed.pathname.startsWith(new URL(assetUrl(dir)).pathname)
    ) || allowSitePath(parsed.pathname)
  )
}

export function isEmbeddableGraphUrl(url: string): boolean {
  return isAutoLoadable(url, (path) => EMBEDDABLE_SITE_PAGES.has(path.split('/').pop() ?? ''))
}
