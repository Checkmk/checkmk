/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The Checkmk pages the SPA links out to, handed in by the page that mounts it.
 *
 * Everything the SPA shows it fetches, but these are not data: they are GUI
 * URLs whose mode names belong to ``cmk.maps.gui`` and would otherwise be
 * mirrored in TypeScript, where a rename breaks the link silently. The
 * dashboard page hands its own out the same way (``page_show_dashboard.py``'s
 * ``links``).
 */
import type { MapsPageLinks } from 'cmk-shared-typing/typescript/maps'
import { type InjectionKey, inject, provide } from 'vue'

export const MAPS_PAGE_LINKS: InjectionKey<MapsPageLinks> = Symbol('mapsPageLinks')

export function provideMapsPageLinks(links: MapsPageLinks): void {
  provide(MAPS_PAGE_LINKS, links)
}

export function useMapsPageLinks(): MapsPageLinks {
  const links = inject(MAPS_PAGE_LINKS)
  if (!links) {
    throw new Error('no provider for MapsPageLinks')
  }
  return links
}
