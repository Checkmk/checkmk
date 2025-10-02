/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { NavItem, NavItemTopic } from 'cmk-shared-typing/typescript/main_menu'

import type { Colors } from '@/components/CmkBadge.vue'

export type OnNavigateCallback = (item: NavItem) => void
export type OnCloseCallback = (id: string) => void
export type OnToggleShowMoreLess = (id: string, show_more_active: boolean) => void
export type OnShowAllTopic = (id: string, topic: NavItemTopic) => void

export interface AjaxResponse<T> {
  result_code: number
  result: T
  severity: 'success' | 'error'
}
/**
 *  AjaxResults
 */
export interface UnackIncompWerksResult {
  count: number
  text: string
  tooltip: string
}

export interface UserMessagesResult {
  popup_messages: UserPopupMessage[]
  hint_messages: UserHintMessages
}

/**
 * Misc
 */

export interface UserPopupMessage {
  id: string
  text: string
  title?: string
}

export interface UserHintMessages {
  type: string
  title: string
  text: string
  count: number
}

export interface MenuItemBadge {
  content: string
  color: Colors
}
