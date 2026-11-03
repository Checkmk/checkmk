/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface CmkMenuLink {
  title: string
  url: string
}

export interface CmkMenuLabelPart {
  text: string
  bold?: boolean
  /** Parts with a lower value give up width first; parts without one never truncate. */
  truncateOrder?: number
}

export interface CmkMenuItem {
  color?: string
  label: CmkMenuLabelPart[]
  links: [CmkMenuLink, ...CmkMenuLink[]]
}
