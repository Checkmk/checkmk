/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'

export interface WidgetItem {
  id: string
  label: TranslatedString
  icon: SimpleIcons
}

export type WidgetItemList = WidgetItem[]
