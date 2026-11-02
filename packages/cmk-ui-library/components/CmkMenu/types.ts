/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'

export interface CmkMenuLink {
  title: string
  url: string
}

export interface CmkMenuLabelPart {
  text: string
  bold?: boolean
  /** Parts with a lower value give up width first; parts without one never truncate. */
  truncateOrder?: number
  /** Once any item uses line 2, every row of the menu gets the two-line height. */
  line?: 1 | 2
}

interface CmkMenuItemBase {
  color?: string
  label: CmkMenuLabelPart[]
  /** Shown at the end of the row. */
  icon?: SimpleIcons
}

/** An item that navigates: to its one link, or through a submenu of several. */
export interface CmkMenuLinkItem extends CmkMenuItemBase {
  links: [CmkMenuLink, ...CmkMenuLink[]]
}

/** An item that picks a value: selecting it emits `select` instead of navigating. */
export interface CmkMenuValueItem extends CmkMenuItemBase {
  value: string
}

export type CmkMenuItem = CmkMenuLinkItem | CmkMenuValueItem
