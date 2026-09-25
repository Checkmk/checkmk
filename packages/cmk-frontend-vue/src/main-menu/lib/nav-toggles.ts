/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { NavItemIdEnum } from 'cmk-shared-typing/typescript/main_menu'
import type { OneColorIcons } from 'cmk-ui-library/components/CmkIcon/types'
import { shallowReactive } from 'vue'

export interface NavToggle {
  icon: OneColorIcons
  isActive: () => boolean
  toggle: () => void
}

const navToggles = shallowReactive(new Map<NavItemIdEnum, NavToggle>())

export function registerNavToggle(id: NavItemIdEnum, navToggle: NavToggle): () => void {
  navToggles.set(id, navToggle)
  return () => {
    if (navToggles.get(id) === navToggle) {
      navToggles.delete(id)
    }
  }
}

export function getNavToggle(id: NavItemIdEnum): NavToggle | undefined {
  return navToggles.get(id)
}
