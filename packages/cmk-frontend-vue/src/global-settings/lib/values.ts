/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'

export type ModificationFilter = 'all' | 'modified' | 'site'

export function isModified(variable: GlobalSettingsVariable): boolean {
  return (
    variable.current.explicit ||
    (variable.current.type === 'site' && variable.current.global_layer.explicit)
  )
}

export function isSiteOverride(variable: GlobalSettingsVariable): boolean {
  return variable.current.type === 'site'
    ? variable.current.explicit
    : variable.current.site_overrides.length > 0
}
