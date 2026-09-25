/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { NavToggleItem } from 'cmk-shared-typing/typescript/main_menu'
import { nextTick } from 'vue'

import MainMenuApp from '@/main-menu/MainMenuApp.vue'
import { registerNavToggle } from '@/main-menu/lib/nav-toggles'

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

vi.mock('@/main-menu/provider/item-vue-apps', () => ({
  lazyMainMenuItemVueAppLoaders: {},
  definedMainMenuItemVueApps: {}
}))

const toggle: NavToggleItem = {
  id: 'ai_assistant',
  type: 'toggle',
  title: 'AI Assistant',
  sort_index: 0,
  shortcut: { key: ' ', ctrl: true, prevent_default: true }
}

function renderMainMenu() {
  render(MainMenuApp, {
    props: {
      start: { title: 'Home', url: '/' },
      main: [],
      user: [],
      toggles: [toggle],
      hide_item_title: false
    }
  })
}

function pressCtrlSpace(): boolean {
  const event = new KeyboardEvent('keydown', { key: ' ', ctrlKey: true, cancelable: true })
  window.dispatchEvent(event)
  window.dispatchEvent(new KeyboardEvent('keyup', { key: ' ', ctrlKey: true }))
  return event.defaultPrevented
}

function registerToggle(onToggle: () => void) {
  return registerNavToggle('ai_assistant', {
    icon: 'sidebar',
    isActive: () => false,
    toggle: onToggle
  })
}

describe('MainMenuApp toggle items', () => {
  test('a toggle item without a registered toggle shows nothing and leaves its key alone', () => {
    renderMainMenu()

    const swallowed = pressCtrlSpace()

    expect(screen.queryByRole('button', { name: /AI Assistant/ })).toBeNull()
    expect(swallowed).toBe(false)
  })

  test('a toggle item appears with its shortcut once its toggle is registered', async () => {
    const onToggle = vi.fn()
    renderMainMenu()
    const unregister = registerToggle(onToggle)
    await nextTick()

    pressCtrlSpace()
    unregister()

    expect(onToggle).toHaveBeenCalledOnce()
  })

  test('a toggle item disappears with its shortcut once its toggle is unregistered', async () => {
    const onToggle = vi.fn()
    renderMainMenu()
    registerToggle(onToggle)()
    await nextTick()

    const swallowed = pressCtrlSpace()

    expect(screen.queryByRole('button', { name: /AI Assistant/ })).toBeNull()
    expect(onToggle).not.toHaveBeenCalled()
    expect(swallowed).toBe(false)
  })
})
