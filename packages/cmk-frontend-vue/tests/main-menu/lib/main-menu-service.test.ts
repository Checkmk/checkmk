/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { NavItemShortcut, NavItems } from 'cmk-shared-typing/typescript/main_menu'
import { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, http } from 'msw'

import { MainMenuService } from '@/main-menu/lib/main-menu-service'

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

const server = useMswServer(
  http.get('*/ajax_sidebar_get_messages.py', () =>
    HttpResponse.json({ result_code: 0, result: userMessages(0) })
  ),
  http.get('*/ajax_sidebar_get_unack_incomp_werks.py', () =>
    HttpResponse.json({ result_code: 0, result: unackIncompWerks(0) })
  )
)

const answerUserMessages = (count: number) =>
  server.use(
    http.get('*/ajax_sidebar_get_messages.py', () =>
      HttpResponse.json({ result_code: 0, result: userMessages(count) })
    )
  )

const answerUnackIncompWerks = (count: number) =>
  server.use(
    http.get('*/ajax_sidebar_get_unack_incomp_werks.py', () =>
      HttpResponse.json({ result_code: 0, result: unackIncompWerks(count) })
    )
  )

const failUserMessages = () =>
  server.use(http.get('*/ajax_sidebar_get_messages.py', () => HttpResponse.error()))

const failUnackIncompWerks = () =>
  server.use(http.get('*/ajax_sidebar_get_unack_incomp_werks.py', () => HttpResponse.error()))

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
    answerUserMessages(3)
    const service = badgedService()
    await vi.waitFor(() => {
      expect(service.getNavItemBadge('user')).toMatchObject({ content: '3' })
    })

    failUserMessages()
    await service.refreshUserMessages()

    expect(service.getNavItemBadge('user')).toBeNull()
  })

  test('clears the help badge when the werks cannot be loaded', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    answerUnackIncompWerks(3)
    const service = badgedService()
    await vi.waitFor(() => {
      expect(service.getNavItemBadge('help')).toMatchObject({ content: '3' })
    })

    failUnackIncompWerks()
    await service.refreshUnackIncompWerks()

    expect(service.getNavItemBadge('help')).toBeNull()
  })
})

describe('main menu service user badge', () => {
  test('clears the user badge once the message count drops to zero', async () => {
    answerUserMessages(3)
    const service = badgedService()
    await vi.waitFor(() => {
      expect(service.getNavItemBadge('user')).toMatchObject({ content: '3' })
    })

    answerUserMessages(0)
    await service.refreshUserMessages()

    expect(service.getNavItemBadge('user')).toBeNull()
  })
})
