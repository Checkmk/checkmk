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
  const titlebarMain = document.createElement('div')
  titlebarMain.className = 'titlebar-main'
  titlebar.append(titlebarMain)
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

test('marks the page heading while the actions sit in the title bar', () => {
  const heading = document.createElement('div')
  heading.id = 'top_heading'
  document.body.append(heading)

  const { unmount } = render(MonitoringHeaderActions)
  expect(heading).toHaveClass('monitoring-header-actions-host')

  unmount()
  expect(heading).not.toHaveClass('monitoring-header-actions-host')
})

test('leaves the page heading alone when the actions go elsewhere', () => {
  const heading = document.createElement('div')
  heading.id = 'top_heading'
  document.body.append(heading)

  render(MonitoringHeaderActions, { props: { teleportTarget: '#page_menu_bar .shortcuts' } })

  expect(heading).not.toHaveClass('monitoring-header-actions-host')
})
