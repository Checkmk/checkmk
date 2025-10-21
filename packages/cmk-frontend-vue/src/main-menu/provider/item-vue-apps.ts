/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

import UnifiedSearchApp from '@/unified-search/UnifiedSearchApp.vue'

import ChangesApp from '../changes/ChangesApp.vue'

export const definedMainMenuItemVueApps: { [key: string]: Component } = {
  'cmk-unified-search': UnifiedSearchApp,
  'cmk-activate-changes': ChangesApp
}
