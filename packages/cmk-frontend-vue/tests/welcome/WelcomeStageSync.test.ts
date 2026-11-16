/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'
import { defineComponent, h } from 'vue'

import WelcomeApp from '@/welcome/WelcomeApp.vue'
import WelcomeSnapin from '@/welcome/components/snapin/WelcomeSnapin.vue'
import { getWelcomeStageInformation } from '@/welcome/components/steps/utils'
import { resetSharedStageInformation } from '@/welcome/composables/useSharedStageInformation'

import { createMockCards } from './mockCards'

vi.mock('@/welcome/components/steps/utils', () => ({
  markStepAsComplete: vi.fn(async () => {}),
  getWelcomeStageInformation: vi.fn()
}))
vi.mock('cmk-ui-library/components/CmkSlideInDialog.vue', () => ({
  default: defineComponent({
    name: 'CmkSlideInDialog',
    props: { open: Boolean, header: Object },
    setup(props, { slots }) {
      return () => (props.open ? h('div', { role: 'dialog' }, slots.default?.()) : null)
    }
  })
}))

const FINISHED_BEFORE: StageInformation['finished'] = ['add_host', 'enable_notifications']

const renderWelcomePageAndSnapin = () => {
  const stageInformation = { finished: FINISHED_BEFORE }
  const page = render(WelcomeApp, {
    props: { cards: createMockCards(), stage_information: stageInformation, is_start_url: false }
  })
  const snapin = render(WelcomeSnapin, {
    props: { cards: createMockCards(), stage_information: stageInformation }
  })
  return {
    page: within(page.container as HTMLElement),
    snapin: within(snapin.container as HTMLElement)
  }
}

beforeEach(() => {
  vi.mocked(getWelcomeStageInformation).mockResolvedValue({
    finished: [...FINISHED_BEFORE, 'create_dashboard']
  })
  localStorage.setItem('create_dashboard-currentStep', JSON.stringify(1))
})

afterEach(() => {
  localStorage.clear()
  resetSharedStageInformation()
})

test('marking a step done in the snapin slideout updates the welcome page', async () => {
  const { page, snapin } = renderWelcomePageAndSnapin()
  expect(page.getByText('2/3 Topics explored')).toBeInTheDocument()

  await fireEvent.click(snapin.getByRole('button', { name: 'Continue exploration' }))
  const slideout = within(screen.getByRole('dialog'))
  await fireEvent.click(slideout.getByRole('button', { name: 'Mark as done' }))

  expect(await page.findByText('3 Topics explored')).toBeInTheDocument()
  expect(page.getByRole('tab', { name: 'Done' })).toBeInTheDocument()
})

test('marking a step done on the welcome page updates the snapin', async () => {
  const { page, snapin } = renderWelcomePageAndSnapin()
  expect(snapin.getByText('2/3 Topics explored')).toBeInTheDocument()

  await fireEvent.click(page.getByRole('button', { name: 'Mark as done' }))

  expect(await snapin.findByText('All steps completed')).toBeInTheDocument()
})

test('a snapin rendered with newer stage information updates the welcome page', async () => {
  const { page } = renderWelcomePageAndSnapin()
  expect(page.getByText('2/3 Topics explored')).toBeInTheDocument()

  render(WelcomeSnapin, {
    props: {
      cards: createMockCards(),
      stage_information: { finished: [...FINISHED_BEFORE, 'create_dashboard'] }
    }
  })

  expect(await page.findByText('3 Topics explored')).toBeInTheDocument()
})
