/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  definedMainMenuItemVueApps,
  lazyMainMenuItemVueAppLoaders
} from '@/main-menu/provider/item-vue-apps'

// The ids below are the contract between the backend NavItem `vue_app.id` config
// and the lookup in ItemPopup.vue (`definedMainMenuItemVueApps[item.vue_app.id]`).
// Locking them here guards against accidental key drift between the loaders map
// and its consumer when the apps are renamed, added or removed.
const EXPECTED_APP_IDS = ['cmk-unified-search', 'cmk-activate-changes']

describe('main menu item vue apps', () => {
  test('lazy loaders expose exactly the expected app ids', () => {
    expect(Object.keys(lazyMainMenuItemVueAppLoaders).sort()).toEqual([...EXPECTED_APP_IDS].sort())
  })

  test('resolved apps map stays in sync with the lazy loaders', () => {
    expect(Object.keys(definedMainMenuItemVueApps).sort()).toEqual(
      Object.keys(lazyMainMenuItemVueAppLoaders).sort()
    )
  })

  test('every expected app id resolves to a component', () => {
    for (const id of EXPECTED_APP_IDS) {
      expect(definedMainMenuItemVueApps[id]).toBeTruthy()
    }
  })
})
