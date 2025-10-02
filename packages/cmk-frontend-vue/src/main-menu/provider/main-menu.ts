/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject } from 'vue'

import type { MainMenuService } from '@/lib/main-menu/service/main-menu'

export const mainMenuKey = Symbol() as InjectionKey<MainMenuService>

export function getInjectedMainMenu(): MainMenuService {
  const mainMenu = inject(mainMenuKey)
  if (mainMenu === undefined) {
    throw Error('can only be used inside menu context')
  }
  return mainMenu
}
