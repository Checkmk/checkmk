/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MonitoringPageLinkButton from '@/monitoring/shared/components/MonitoringPageLinkButton.vue'

const PROPS = { url: 'monitor_all_hosts.py', title: 'Try the new "All hosts" view' }

let pageState: HTMLElement
let pageMenuBar: HTMLElement
let shortcuts: HTMLElement

beforeEach(() => {
  pageState = document.createElement('div')
  pageState.className = 'page_state'
  pageMenuBar = document.createElement('div')
  pageMenuBar.id = 'page_menu_bar'
  shortcuts = document.createElement('div')
  shortcuts.className = 'shortcuts'
  pageMenuBar.appendChild(shortcuts)
  document.body.append(pageState, pageMenuBar)
})

afterEach(() => {
  pageState.remove()
  pageMenuBar.remove()
})

test('renders into the page state area by default', () => {
  render(MonitoringPageLinkButton, { props: PROPS })

  expect(pageState).toContainElement(screen.getByRole('button', { name: /All hosts/ }))
})

test('renders into the given teleport target', () => {
  render(MonitoringPageLinkButton, {
    props: { ...PROPS, teleport_target: '#page_menu_bar .shortcuts' }
  })

  expect(shortcuts).toContainElement(screen.getByRole('button', { name: /All hosts/ }))
})

test('offers no feedback link without a survey URL', () => {
  render(MonitoringPageLinkButton, { props: PROPS })

  expect(screen.queryByRole('link', { name: /Give feedback/ })).toBeNull()
})

test('offers a feedback link next to the button when given a survey URL', () => {
  render(MonitoringPageLinkButton, {
    props: { ...PROPS, survey_url: 'https://survey.example.com/1' }
  })

  const link = screen.getByRole('link', { name: /Give feedback/ })
  expect(link).toHaveAttribute('href', 'https://survey.example.com/1')
  expect(pageState).toContainElement(link)
})
