/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'

import WelcomeApp from '@/welcome/WelcomeApp.vue'
import { getWelcomeStageInformation } from '@/welcome/components/steps/utils'

import { createMockCards } from './mockCards'

vi.mock('@/welcome/components/steps/utils', () => ({
  markStepAsComplete: vi.fn(async () => {}),
  getWelcomeStageInformation: vi.fn()
}))
vi.mock('@/sidebar/lib/snapin-refresh', () => ({ refreshSidebarSnapin: vi.fn() }))

const ASSIGN = 'Assign responsibilities with contact groups'
const ONBOARDING_DONE: StageInformation['finished'] = [
  'add_host',
  'enable_notifications',
  'create_dashboard'
]

const renderApp = (finished: StageInformation['finished']) =>
  render(WelcomeApp, {
    props: { cards: createMockCards(), stage_information: { finished }, is_start_url: false }
  })

afterEach(() => localStorage.clear())

test('further guides stay hidden until the onboarding is complete', () => {
  renderApp(['add_host', 'enable_notifications'])

  expect(screen.queryByText('To explore')).not.toBeInTheDocument()
  expect(screen.queryByText(ASSIGN)).not.toBeInTheDocument()
})

test('a complete onboarding shows the further guides to explore', () => {
  renderApp(ONBOARDING_DONE)

  expect(screen.getByText('To explore')).toBeInTheDocument()
  expect(screen.getByText('Done')).toBeInTheDocument()
  expect(screen.getByText(ASSIGN)).toBeInTheDocument()
})

test('a guide finished in "To explore" moves to "Done"', async () => {
  vi.mocked(getWelcomeStageInformation).mockResolvedValue({
    finished: [...ONBOARDING_DONE, 'assign_responsibilities']
  })
  localStorage.setItem('assign_responsibilities-currentStep', JSON.stringify(2))
  renderApp(ONBOARDING_DONE)

  await fireEvent.click(screen.getByText(ASSIGN))
  await fireEvent.click(await screen.findByRole('button', { name: 'Mark as done' }))

  await waitFor(() => expect(screen.queryByText(ASSIGN)).not.toBeInTheDocument())
  await fireEvent.mouseDown(screen.getByRole('tab', { name: 'Done' }))
  expect(await screen.findByText(ASSIGN)).toBeInTheDocument()
})
