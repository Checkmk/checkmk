/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { NavItemTopicEntry } from 'cmk-shared-typing/typescript/main_menu'
import { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import NavItemTopicEntryLink from '@/main-menu/components/popup/NavItemTopicEntryLink.vue'
import { MainMenuService } from '@/main-menu/lib/main-menu-service'
import { mainMenuKey } from '@/main-menu/provider/main-menu'

vi.mock('@/main-menu/lib/main-menu-api-client', () => ({
  MainMenuApiClient: class {
    async getUserMessages() {
      return {
        hint_messages: { type: 'gui_hint', title: 'Messages', text: 'new', count: 1 },
        popup_messages: []
      }
    }

    async getUnacknowledgedIncompatibleWerks() {
      return { count: 0, text: '', tooltip: '' }
    }
  }
}))

const receivedMessages: NavItemTopicEntry = {
  id: 'user_messages',
  title: 'Received messages',
  url: 'user_message.py',
  sort_index: 10,
  chip: { mode: 'user-messages-hint', color: 'danger' }
}

describe('user messages chip', () => {
  test('appears once the user messages arrive after the entry was rendered', async () => {
    render(NavItemTopicEntryLink, {
      global: {
        provide: { [mainMenuKey]: new MainMenuService([], [], new KeyShortcutService(window)) }
      },
      props: { entry: receivedMessages, navItemId: 'user' }
    })
    expect(screen.queryByText('1 new')).toBeNull()

    expect(await screen.findByText('1 new')).toBeVisible()
  })
})
