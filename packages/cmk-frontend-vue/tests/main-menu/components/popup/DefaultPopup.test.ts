/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { NavItemHeader } from 'cmk-shared-typing/typescript/main_menu'
import { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import DefaultPopup from '@/main-menu/components/popup/DefaultPopup.vue'
import { MainMenuService } from '@/main-menu/lib/main-menu-service'
import { mainMenuKey } from '@/main-menu/provider/main-menu'

vi.mock('@/main-menu/lib/main-menu-api-client', () => ({
  MainMenuApiClient: class {
    async getUserMessages() {
      return {
        hint_messages: { type: 'gui_hint', title: '', text: '', count: 0 },
        popup_messages: []
      }
    }

    async getUnacknowledgedIncompatibleWerks() {
      return { count: 8, text: 'Unacknowledged werks', tooltip: '' }
    }
  }
}))

const header: NavItemHeader = {
  trigger_button: { mode: 'unack-incomp-werks', color: 'danger', target_url: 'werk.py' }
}

describe('unacknowledged werks trigger button', () => {
  test('appears once the werk count arrives after the popup was rendered', async () => {
    render(DefaultPopup, {
      global: {
        provide: { [mainMenuKey]: new MainMenuService([], [], new KeyShortcutService(window)) }
      },
      props: { navItemId: 'help', header }
    })
    expect(screen.queryByText('Unacknowledged werks')).toBeNull()

    expect(await screen.findByText('Unacknowledged werks')).toBeVisible()
  })
})
