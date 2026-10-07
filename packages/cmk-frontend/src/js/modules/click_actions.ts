/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KnownClickAction } from 'cmk-shared-typing/typescript/legacy_frontend_hooks'

import { call_ajax } from '@/modules/ajax'
import { add_bookmark, update_vue_snapin_contents } from '@/modules/sidebar'

import { type ClickAction, register_click_actions } from './click_action_dispatcher'

const click_actions: Record<KnownClickAction, ClickAction> = {
  add_bookmark: () => add_bookmark(),
  reload_page: () => location.reload(),
  switch_master_state: (_element, options) => {
    call_ajax(options.url, {
      method: 'POST',
      response_handler: update_vue_snapin_contents,
      handler_data: 'snapin_master_control'
    })
  }
}

register_click_actions(click_actions)
