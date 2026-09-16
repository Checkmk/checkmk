/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'

import type { GlobalSettingsScope } from '../api'

export function isModified(variable: GlobalSettingsVariable): boolean {
  return variable.origin !== 'factory'
}

export function isSiteOverride(variable: GlobalSettingsVariable): boolean {
  return variable.origin === 'site'
}

/** The scope holds the explicit value, so removing it here falls back to the layer below. */
export function isExplicitIn(
  variable: GlobalSettingsVariable,
  scope: GlobalSettingsScope
): boolean {
  return variable.origin === scope.type
}
