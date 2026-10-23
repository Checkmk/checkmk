/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { DashboardOwnerType } from '@/dashboard/types/dashboard'

export interface SelectedDashboard {
  name: string
  owner: string
  title: string
  type: DashboardOwnerType
}

/** A menu button needs an accessible name: its visible label, or an aria-label if it only shows an icon. */
export type MenuButtonName =
  | { label: TranslatedString; ariaLabel?: TranslatedString }
  | { label?: undefined; ariaLabel: TranslatedString }
