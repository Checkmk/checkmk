/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { NavItemShortcut, NavItems } from 'cmk-shared-typing/typescript/main_menu'
import { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import { MainMenuService } from '@/main-menu/lib/main-menu-service'

const api = vi.hoisted(() => ({
  getUserMessages: vi.fn(),
  getUnacknowledgedIncompatibleWerks: vi.fn()
}))

vi.mock('@/main-menu/lib/main-menu-api-client', () => ({
  MainMenuApiClient: class {
    getUserMessages = api.getUserMessages
    getUnacknowledgedIncompatibleWerks = api.getUnacknowledgedIncompatibleWerks
  }
}))

class RefreshableMainMenuService extends MainMenuService {
  public refreshUserMessages(): Promise<void> {
    return this.updateUserMessages()
  }

  public refreshUnackIncompWerks(): Promise<void> {
    return this.updateUnacknowledgedIncompatibleWerks()
  }
}

const userMessages = (count: number) => ({
  hint_messages: { type: 'message', title: 'Messages', text: 'unread messages', count },
  popup_messages: []
})

const unackIncompWerks = (count: number) => ({ count, text: 'werks', tooltip: '' })

beforeEach(() => {
  api.getUserMessages.mockResolvedValue(userMessages(0))
  api.getUnacknowledgedIncompatibleWerks.mockResolvedValue(unackIncompWerks(0))
})

afterEach(() => {
  vi.restoreAllMocks()
})

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

const mainItems: NavItems = [
  {
    id: 'help',
    type: 'item',
    title: 'Help',
    sort_index: 20,
    shortcut: { key: 'h', alt: true }
  }
]

const userItems: NavItems = [
  {
    id: 'user',
    type: 'item',
    title: 'User',
    sort_index: 30,
    shortcut: { key: 'u', alt: true }
  }
]

const badgedService = () =>
  new RefreshableMainMenuService(mainItems, userItems, new KeyShortcutService(window))

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

describe('main menu service failing requests', () => {
  test('clears the user badge when the messages cannot be loaded', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    api.getUserMessages.mockResolvedValue(userMessages(3))
    const service = badgedService()
    await vi.waitFor(() => {
      expect(service.getNavItemBadge('user')).toMatchObject({ content: '3' })
    })

    api.getUserMessages.mockRejectedValue(new Error('request failed'))
    await service.refreshUserMessages()

    expect(service.getNavItemBadge('user')).toBeNull()
  })

  test('clears the help badge when the werks cannot be loaded', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    api.getUnacknowledgedIncompatibleWerks.mockResolvedValue(unackIncompWerks(3))
    const service = badgedService()
    await vi.waitFor(() => {
      expect(service.getNavItemBadge('help')).toMatchObject({ content: '3' })
    })

    api.getUnacknowledgedIncompatibleWerks.mockRejectedValue(new Error('request failed'))
    await service.refreshUnackIncompWerks()

    expect(service.getNavItemBadge('help')).toBeNull()
  })
})
