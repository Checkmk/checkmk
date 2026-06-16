/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type AsyncComponentLoader, type Component, defineAsyncComponent } from 'vue'

// Loaders for the nav popup apps. They are kept out of the nav/sidebar bundle's
// critical path and loaded lazily. Exported so the navigation can warm them in
// the background once it has mounted (see MainMenuApp), independent of when
// their popup renders.
export const lazyMainMenuItemVueAppLoaders: { [key: string]: AsyncComponentLoader } = {
  'cmk-unified-search': () => import('@/unified-search/UnifiedSearchApp.vue'),
  'cmk-activate-changes': () => import('../changes/ChangesApp.vue')
}

export const definedMainMenuItemVueApps: { [key: string]: Component } = Object.fromEntries(
  Object.entries(lazyMainMenuItemVueAppLoaders).map(([id, loader]) => [
    id,
    defineAsyncComponent(loader)
  ])
)
