/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { NavToggleItem as NavToggleItemType } from 'cmk-shared-typing/typescript/main_menu'
import { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { ref } from 'vue'

import NavToggleItem from '@/main-menu/components/NavToggleItem.vue'
import { MainMenuService } from '@/main-menu/lib/main-menu-service'
import type { NavToggle } from '@/main-menu/lib/nav-toggles'
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

const item: NavToggleItemType = {
  id: 'ai_assistant',
  type: 'toggle',
  title: 'AI Assistant',
  sort_index: 0,
  shortcut: { key: ' ', ctrl: true, prevent_default: true },
  hint: 'Open the AI assistant'
}

function openState(highlight?: NavToggle['highlight']) {
  const open = ref(false)
  const navToggle: NavToggle = {
    icon: 'sidebar',
    ...(highlight !== undefined && { highlight }),
    isActive: () => open.value,
    toggle: () => {
      open.value = !open.value
    }
  }
  return { open, navToggle }
}

function renderToggle(navToggle: NavToggle) {
  return render(NavToggleItem, {
    global: {
      provide: { [mainMenuKey]: new MainMenuService([], [], new KeyShortcutService(window)) }
    },
    props: { item, navToggle, hideItemTitle: false }
  })
}

function pressCtrlSpace(): boolean {
  const event = new KeyboardEvent('keydown', { key: ' ', ctrlKey: true, cancelable: true })
  window.dispatchEvent(event)
  window.dispatchEvent(new KeyboardEvent('keyup', { key: ' ', ctrlKey: true }))
  return event.defaultPrevented
}

describe('NavToggleItem', () => {
  test('shows the hint as its tooltip', () => {
    renderToggle(openState().navToggle)

    expect(screen.getByTitle('Open the AI assistant')).toBeInTheDocument()
  })

  test('clicking flips the registered state and the pressed state follows it', async () => {
    const { open, navToggle } = openState()
    renderToggle(navToggle)
    const toggle = screen.getByRole('button', { name: /AI Assistant/ })
    expect(toggle).toHaveAttribute('aria-pressed', 'false')

    await userEvent.click(toggle)

    expect(open.value).toBe(true)
    expect(toggle).toHaveAttribute('aria-pressed', 'true')
  })

  test('its shortcut flips the toggle and keeps the key from the browser', () => {
    const { open, navToggle } = openState()
    renderToggle(navToggle)

    const swallowed = pressCtrlSpace()

    expect(open.value).toBe(true)
    expect(swallowed).toBe(true)
  })

  test('highlights itself in the AI colour when its toggle asks for it', () => {
    renderToggle(openState('ai').navToggle)

    expect(screen.getByRole('listitem')).toHaveClass('mm-nav-toggle-item__li--highlight-ai')
  })

  test('highlights itself in the default colour when its toggle asks for none', () => {
    renderToggle(openState().navToggle)

    expect(screen.getByRole('listitem')).not.toHaveClass('mm-nav-toggle-item__li--highlight-ai')
  })

  test('unmounting frees its shortcut key', () => {
    const { open, navToggle } = openState()
    renderToggle(navToggle).unmount()

    const swallowed = pressCtrlSpace()

    expect(open.value).toBe(false)
    expect(swallowed).toBe(false)
  })
})
