/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MonitoringLegacyViewButton from '@/monitoring/shared/components/MonitoringLegacyViewButton.vue'

const PROPS = { url: 'view.py?view_name=allhosts', title: 'Return to classic view' }

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
  render(MonitoringLegacyViewButton, { props: PROPS })

  expect(titlebar).toContainElement(screen.getByRole('button', { name: /classic view/ }))
})

test('renders into the given teleport target', () => {
  render(MonitoringLegacyViewButton, {
    props: { ...PROPS, teleport_target: '#page_menu_bar .shortcuts' }
  })

  expect(shortcuts).toContainElement(screen.getByRole('button', { name: /classic view/ }))
})

test('falls back to the title bar when no teleport target is given', () => {
  render(MonitoringLegacyViewButton, { props: { ...PROPS, teleport_target: null } })

  expect(titlebar).toContainElement(screen.getByRole('button', { name: /classic view/ }))
})
