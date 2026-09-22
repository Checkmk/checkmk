/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MonitoringSurveyLink from '@/monitoring/shared/components/MonitoringSurveyLink.vue'

const SURVEY_URL = 'https://survey.example/new-view'

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
  render(MonitoringSurveyLink, { props: { url: SURVEY_URL } })

  expect(titlebar).toContainElement(screen.getByRole('link', { name: /Give feedback/ }))
})

test('renders into the given teleport target', () => {
  render(MonitoringSurveyLink, {
    props: { url: SURVEY_URL, teleportTarget: '#page_menu_bar .shortcuts' }
  })

  expect(shortcuts).toContainElement(screen.getByRole('link', { name: /Give feedback/ }))
})

test('points at the survey and opens it in a new tab', () => {
  render(MonitoringSurveyLink, { props: { url: SURVEY_URL } })

  const link = screen.getByRole('link', { name: /Give feedback/ })

  expect(link).toHaveAttribute('href', SURVEY_URL)
  expect(link).toHaveAttribute('target', '_blank')
})
