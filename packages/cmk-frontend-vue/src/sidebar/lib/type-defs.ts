/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface SidebarSnapinContents {
  [key: string]: string | null
}

export type OnUpdateSnapinContent = (contents: SidebarSnapinContents) => void

export interface AddSnapinResponse {
  name: string
  url: string
  content: string
}

export interface TSidebarSnapin {
  name: string
  title: string
  refresh_regularly?: boolean | undefined
  refresh_on_restart?: boolean | undefined
  has_show_more_items?: boolean | undefined
  open?: boolean | undefined
  show_more_active?: boolean | undefined
  content?: string | undefined
  description?: string | undefined
}
