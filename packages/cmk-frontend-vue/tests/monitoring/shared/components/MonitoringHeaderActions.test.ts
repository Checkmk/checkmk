/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { h } from 'vue'

import MonitoringHeaderActions from '@/monitoring/shared/components/MonitoringHeaderActions.vue'

let titlebar: HTMLElement
let shortcuts: HTMLElement

beforeEach(() => {
  titlebar = document.createElement('div')
  titlebar.className = 'titlebar'
  const pageMenuBar = document.createElement('div')
  pageMenuBar.id = 'page_menu_bar'
  shortcuts = document.createElement('div')
  shortcuts.className = 'shortcuts'
  pageMenuBar.appendChild(shortcuts)
  document.body.append(titlebar, pageMenuBar)
})

afterEach(() => {
  document.body.replaceChildren()
})

test('renders into the title bar by default', () => {
  render(MonitoringHeaderActions, {
    slots: { default: () => h('a', { href: '#' }, 'feedback') }
  })

  expect(titlebar).toContainElement(screen.getByRole('link', { name: 'feedback' }))
})

test('renders into the given teleport target', () => {
  render(MonitoringHeaderActions, {
    props: { teleportTarget: '#page_menu_bar .shortcuts' },
    slots: { default: () => h('a', { href: '#' }, 'feedback') }
  })

  expect(shortcuts).toContainElement(screen.getByRole('link', { name: 'feedback' }))
})

test('falls back to the title bar when no teleport target is given', () => {
  render(MonitoringHeaderActions, {
    props: { teleportTarget: null },
    slots: { default: () => h('a', { href: '#' }, 'feedback') }
  })

  expect(titlebar).toContainElement(screen.getByRole('link', { name: 'feedback' }))
})

test('keeps all actions together in one box', () => {
  render(MonitoringHeaderActions, {
    props: { teleportTarget: '#page_menu_bar .shortcuts' },
    slots: {
      default: () => [h('a', { href: '#' }, 'feedback'), h('button', 'back to legacy')]
    }
  })

  const box = screen.getByRole('link', { name: 'feedback' }).parentElement

  expect(box).toContainElement(screen.getByRole('button', { name: 'back to legacy' }))
  expect(shortcuts).toContainElement(box)
})
