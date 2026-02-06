/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import type { StageInformation, WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import { defineComponent, h, ref } from 'vue'

import WelcomeSnapin from '@/welcome/components/snapin/WelcomeSnapin.vue'

// Mock CmkSlideInDialog to avoid Radix-Vue portal issues in test environment
vi.mock('@/components/CmkSlideInDialog.vue', () => ({
  default: defineComponent({
    name: 'CmkSlideInDialog',
    props: {
      open: Boolean,
      header: Object,
      isIndexPage: Boolean
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

const createMockCards = (): WelcomeCards => ({
  add_folder: 'add_folder.py',
  checkmk_ai: 'https://checkmk.com/ai',
  checkmk_docs: 'https://docs.checkmk.com',
  checkmk_forum: 'https://forum.checkmk.com',
  checkmk_best_practices: 'https://checkmk.com/best-practices',
  checkmk_trainings: 'https://checkmk.com/trainings',
  checkmk_webinars: 'https://checkmk.com/webinars',
  create_contactgroups: 'wato.py?mode=contact_groups',
  users: 'wato.py?mode=users',
  assign_host_to_contactgroups: 'wato.py?mode=edit_host',
  setup_backup: 'wato.py?mode=backup',
  scale_monitoring: 'wato.py?mode=distributed_monitoring',
  fine_tune_monitoring: 'wato.py?mode=globalvars',
  add_host: 'wato.py?mode=newhost',
  network_devices: 'wato.py?mode=newhost&host_type=snmp',
  aws_quick_setup: 'quick_setup.py?mode=aws',
  azure_quick_setup: 'quick_setup.py?mode=azure',
  gcp_quick_setup: 'quick_setup.py?mode=gcp',
  activate_changes: 'wato.py?mode=changelog',
  setup_hosts: 'wato.py?mode=folder',
  main_dashboard: 'dashboard.py?name=main',
  problem_dashboard: 'dashboard.py?name=problems',
  unhandled_service_problems: 'view.py?view_name=svcproblems',
  time_periods: 'wato.py?mode=timeperiods',
  host_groups: 'wato.py?mode=host_groups',
  add_notification_rule: 'wato.py?mode=notification_rule',
  test_notifications: 'wato.py?mode=notifications',
  add_custom_dashboard: 'dashboard.py?mode=create',
  all_dashboards: 'dashboard.py',
  mark_step_completed: '/api/welcome/mark_step_completed',
  get_stage_information: '/api/welcome/get_stage_information',
  intro_users: 'https://docs.checkmk.com/2.5.0/en/intro_users.html?origin=checkmk',
  intro_notifications: 'https://docs.checkmk.com/2.5.0/en/intro_notifications.html?origin=checkmk',
  setup_folder_structure: 'https://docs.checkmk.com/2.5.0/en/host_structure.html?origin=checkmk',
  start_page: 'user_profile.py'
})

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
