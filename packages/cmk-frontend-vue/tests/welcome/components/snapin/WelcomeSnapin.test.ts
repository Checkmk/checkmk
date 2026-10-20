/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'
import { defineComponent, h, ref } from 'vue'

import WelcomeSnapin from '@/welcome/components/snapin/WelcomeSnapin.vue'

import { createMockCards } from '../../mockCards'

// Mock CmkSlideInDialog to avoid Radix-Vue portal issues in test environment
vi.mock('cmk-ui-library/components/CmkSlideInDialog.vue', () => ({
  default: defineComponent({
    name: 'CmkSlideInDialog',
    props: {
      open: Boolean,
      header: Object
    },
    emits: ['close'],
    setup(props, { slots }) {
      return () => {
        if (!props.open) {
          return null
        }
        return h('div', { role: 'dialog', 'data-testid': 'slideout-dialog' }, [
          h('h2', props.header?.title),
          slots.default?.()
        ])
      }
    }
  })
}))

test('clicking "Continue exploration" button on sidebar snapin opens slideout with welcome steps', async () => {
  const mockCards = createMockCards()
  const mockStageInfo: StageInformation = {
    finished: []
  }

  const testComponent = defineComponent({
    components: { WelcomeSnapin },
    setup() {
      const cards = ref(mockCards)
      const stageInfo = ref(mockStageInfo)
      return { cards, stageInfo }
    },
    template: `
      <WelcomeSnapin
        :cards="cards"
        :stage_information="stageInfo"
      />
    `
  })

  const { container } = render(testComponent)

  const continueExplorationButton = within(container as HTMLElement).getByRole('button', {
    name: 'Continue exploration'
  })
  expect(continueExplorationButton).toBeInTheDocument()

  expect(screen.queryByTestId('slideout-dialog')).not.toBeInTheDocument()

  await fireEvent.click(continueExplorationButton)

  const closeButton = within(container as HTMLElement).getByRole('button', { name: 'Close' })
  expect(closeButton).toBeInTheDocument()

  const slideout = await screen.findByTestId('slideout-dialog')
  expect(slideout).toBeInTheDocument()

  expect(within(slideout as HTMLElement).getByText('Topics to explore')).toBeInTheDocument()

  const onboardingSteps = within(slideout as HTMLElement).getByTestId('onboarding-steps')
  expect(onboardingSteps).toBeInTheDocument()
})

test('progress counts only current onboarding steps', () => {
  render(WelcomeSnapin, {
    props: {
      cards: createMockCards(),
      stage_information: { finished: ['add_host', 'adjust_services'] }
    }
  })

  expect(screen.getByText('1/3 Topics explored')).toBeInTheDocument()
})
