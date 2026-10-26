/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, provide } from 'vue'

import type { MapListView } from '@/maps/types/api'

/**
 * Cards or table for the map list. ``maps.py`` decides it (the URL, else what
 * this user last chose, else the global setting) because it renders the page
 * menu that offers the other one; the list only shows what it was handed.
 */
export const MAP_LIST_LAYOUT: InjectionKey<MapListView> = Symbol('mapListLayout')

export function provideMapListLayout(layout: MapListView): void {
  provide(MAP_LIST_LAYOUT, layout)
}

export function useMapListViewMode(): { viewMode: MapListView } {
  const viewMode = inject(MAP_LIST_LAYOUT)
  if (!viewMode) {
    throw new Error('no provider for the map list layout')
  }
  return { viewMode }
}
