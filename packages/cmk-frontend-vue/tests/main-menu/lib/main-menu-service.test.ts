/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { NavItemShortcut, NavItems } from 'cmk-shared-typing/typescript/main_menu'
import { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import { MainMenuService } from '@/main-menu/lib/main-menu-service'

vi.mock('@/main-menu/lib/main-menu-api-client', () => ({
  MainMenuApiClient: class {
    async getUserMessages() {
      return { hint_messages: { count: 0, title: '' }, popup_messages: [] }
    }

    async getUnacknowledgedIncompatibleWerks() {
      return { count: 0 }
    }
  }
}))

const navItems = (shortcut: NavItemShortcut): NavItems => [
  {
    id: 'setup',
    type: 'item',
    title: 'Setup',
    sort_index: 10,
    shortcut
  }
]

const registeredShortcut = (shortcut: NavItemShortcut) => {
  const shortCutService = new KeyShortcutService(window)
  const on = vi.spyOn(shortCutService, 'on')
  new MainMenuService(navItems(shortcut), [], shortCutService)
  return on.mock.calls[0]![0]
}

describe('main menu service shortcut registration', () => {
  test('forwards prevent_default so the browser binding stays silent', () => {
    expect(registeredShortcut({ key: 's', alt: true, prevent_default: true })).toMatchObject({
      key: ['s'],
      alt: true,
      preventDefault: true
    })
  })

  test('leaves the browser binding alone when prevent_default is unset', () => {
    expect(registeredShortcut({ key: 's', alt: true })).toMatchObject({
      preventDefault: false
    })
  })
})
