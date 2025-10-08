/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject } from 'vue'

import type { SidebarService } from '@/lib/sidebar/sidebar'

export const sidebarKey = Symbol() as InjectionKey<SidebarService>

export function getInjectedSidebar(): SidebarService {
  const sidebar = inject(sidebarKey)
  if (sidebar === undefined) {
    throw Error('can only be used inside menu context')
  }
  return sidebar
}
