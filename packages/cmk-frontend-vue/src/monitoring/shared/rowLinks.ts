/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

/** A link the backend offers on every row, e.g. into Setup, its url keeping the row's placeholders. */
export interface RowLink {
  ident: string
  title: string
  icon: string
  url: string
}

/** The inline button of a row link. */
export function toCellAction(link: RowLink): CellAction {
  return {
    id: link.ident,
    label: link.title as TranslatedString,
    icon: link.icon as SimpleIcons,
    url: link.url
  }
}
