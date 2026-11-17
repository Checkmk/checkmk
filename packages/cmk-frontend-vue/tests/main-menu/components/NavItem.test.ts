/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { NavItem as NavItemType } from 'cmk-shared-typing/typescript/main_menu'
import { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import NavItem from '@/main-menu/components/NavItem.vue'
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
      return { count: 0, text: '', tooltip: '' }
    }
  }
}))

const item: NavItemType = {
  id: 'monitoring',
  type: 'item',
  title: 'Monitor',
  sort_index: 0,
  shortcut: { key: 'm', alt: true },
  hint: 'Monitor hosts and services'
}

describe('NavItem', () => {
  test('shows the hint as its tooltip while the navigation bar hides the item titles', () => {
    render(NavItem, {
      global: {
        provide: { [mainMenuKey]: new MainMenuService([], [], new KeyShortcutService(window)) }
      },
      props: { item, hideItemTitle: true }
    })

    expect(screen.getByRole('listitem')).toHaveAttribute('title', 'Monitor hosts and services')
  })
})
