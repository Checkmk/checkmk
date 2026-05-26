/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'

/** Minimal two-step wizard for testing mechanics. */
const twoStepOverviewWizard = defineComponent({
  components: { CmkWizard, CmkWizardStep },
  setup() {
    const currentStep = ref(1)
    return { currentStep }
  },
  template: `
    <CmkWizard v-model="currentStep" mode="overview">
      <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
        <template #header><h2>Step 1 heading</h2></template>
        <template #content><div data-testid="content-1">Content 1</div></template>
      </CmkWizardStep>
      <CmkWizardStep :index="2" :is-completed="() => currentStep > 2">
        <template #header><h2>Step 2 heading</h2></template>
        <template #content><div data-testid="content-2">Content 2</div></template>
      </CmkWizardStep>
    </CmkWizard>
  `
})

const twoStepOverviewWizardWithButtons = defineComponent({
  components: { CmkWizard, CmkWizardStep, CmkWizardButton },
  setup() {
    const currentStep = ref(1)
    return { currentStep }
  },
  template: `
    <CmkWizard v-model="currentStep" mode="overview">
      <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
        <template #header><h2>Step 1 heading</h2></template>
        <template #content><div data-testid="content-1">Content 1</div></template>
        <template #actions>
          <CmkWizardButton type="next" />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
      <CmkWizardStep :index="2" :is-completed="() => currentStep > 2">
        <template #header><h2>Step 2 heading</h2></template>
        <template #content><div data-testid="content-2">Content 2</div></template>
        <template #actions>
          <CmkWizardButton type="finish" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  `
})

const twoStepWizard = defineComponent({
  components: { CmkWizard, CmkWizardStep, CmkWizardButton },
  setup() {
    const currentStep = ref(1)
    return { currentStep }
  },
  template: `
    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
        <template #header><h2>Step 1 heading</h2></template>
        <template #content><div data-testid="content-1">Content 1</div></template>
        <template #actions>
          <CmkWizardButton type="next" />
        </template>
      </CmkWizardStep>
      <CmkWizardStep :index="2" :is-completed="() => currentStep > 2">
        <template #header><h2>Step 2 heading</h2></template>
        <template #content><div data-testid="content-2">Content 2</div></template>
        <template #actions>
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  `
})

describe('CmkWizardStep', () => {
  test('active step content is visible, inactive step content is hidden', () => {
    render(twoStepWizard)

    expect(screen.getByTestId('content-1')).toBeVisible()
    expect(screen.getByTestId('content-2')).not.toBeVisible()
  })

  test('inactive step content becomes visible after navigating to it', async () => {
    const user = userEvent.setup()
    render(twoStepWizard)

    await user.click(screen.getByRole('button', { name: /next step/i }))

    expect(screen.getByTestId('content-1')).not.toBeVisible()
    expect(screen.getByTestId('content-2')).toBeVisible()
  })

  test('active step has aria-current="step"', () => {
    render(twoStepWizard)

    expect(screen.getAllByRole('listitem', { current: 'step' })).toHaveLength(1)
  })

  test('aria-current moves to newly active step after navigation', async () => {
    const user = userEvent.setup()
    render(twoStepWizard)

    await user.click(screen.getByRole('button', { name: /next step/i }))

    const [, step2] = screen.getAllByRole('listitem')
    expect(screen.getByRole('listitem', { current: 'step' })).toBe(step2)
  })

  test('Previous button goes back to previous step', async () => {
    const user = userEvent.setup()
    render(twoStepWizard)

    await user.click(screen.getByRole('button', { name: /next step/i }))
    expect(screen.getByTestId('content-2')).toBeVisible()

    await user.click(screen.getByRole('button', { name: /previous step/i }))
    expect(screen.getByTestId('content-1')).toBeVisible()
    expect(screen.getByTestId('content-2')).not.toBeVisible()
  })

  test('clicking a completed step header navigates back to it', async () => {
    const user = userEvent.setup()
    render(twoStepWizard)

    // Advance to step 2 so step 1 becomes completed
    await user.click(screen.getByRole('button', { name: /next step/i }))
    expect(screen.getByTestId('content-2')).toBeVisible()

    // Click step 1's heading — it is completed, so it should jump back
    await user.click(screen.getByText('Step 1 heading'))
    expect(screen.getByTestId('content-1')).toBeVisible()
    expect(screen.getByTestId('content-2')).not.toBeVisible()
  })

  test('clicking an incomplete step header does not navigate', async () => {
    const user = userEvent.setup()
    render(twoStepWizard)

    // Step 2 is incomplete — clicking its heading should do nothing
    await user.click(screen.getByText('Step 2 heading'))
    expect(screen.getByTestId('content-1')).toBeVisible()
    expect(screen.getByTestId('content-2')).not.toBeVisible()
  })
})

describe('CmkWizardStep locked wizard', () => {
  const twoStepLockedWizard = defineComponent({
    components: { CmkWizard, CmkWizardStep, CmkWizardButton },
    setup() {
      // Start on step 2 so step 1 is "completed" — that's the post-save
      // shape where the wizard gets locked.
      const currentStep = ref(2)
      return { currentStep }
    },
    template: `
      <CmkWizard v-model="currentStep" mode="guided" :locked="true">
        <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
          <template #header><h2>Step 1 heading</h2></template>
          <template #content><div data-testid="content-1">Content 1</div></template>
        </CmkWizardStep>
        <CmkWizardStep :index="2" :is-completed="() => currentStep > 2">
          <template #header><h2>Step 2 heading</h2></template>
          <template #content><div data-testid="content-2">Content 2</div></template>
          <template #actions>
            <CmkWizardButton type="previous" />
          </template>
        </CmkWizardStep>
      </CmkWizard>
    `
  })

  test('Previous button does not navigate when wizard is locked', async () => {
    const user = userEvent.setup()
    render(twoStepLockedWizard)

    expect(screen.getByTestId('content-2')).toBeVisible()

    await user.click(screen.getByRole('button', { name: /previous step/i }))

    // Still on step 2 — navigation was blocked.
    expect(screen.getByTestId('content-2')).toBeVisible()
    expect(screen.getByTestId('content-1')).not.toBeVisible()
  })

  test('clicking a completed step header does not navigate when locked', async () => {
    const user = userEvent.setup()
    render(twoStepLockedWizard)

    await user.click(screen.getByText('Step 1 heading'))

    // Step 1 is completed but the locked wizard refused the jump.
    expect(screen.getByTestId('content-2')).toBeVisible()
    expect(screen.getByTestId('content-1')).not.toBeVisible()
  })
})

describe('CmkWizardStep overview mode', () => {
  test('all step content is visible simultaneously', () => {
    render(twoStepOverviewWizard)

    expect(screen.getByTestId('content-1')).toBeVisible()
    expect(screen.getByTestId('content-2')).toBeVisible()
  })

  test('aria-current is set on the active step', () => {
    render(twoStepOverviewWizard)

    const [step1, step2] = screen.getAllByRole('listitem')
    expect(step1).toHaveAttribute('aria-current', 'step')
    expect(step2).not.toHaveAttribute('aria-current')
  })

  test('clicking a step header does not navigate', async () => {
    const user = userEvent.setup()
    render(twoStepOverviewWizard)

    await user.click(screen.getByText('Step 2 heading'))

    expect(screen.getAllByRole('listitem', { current: 'step' })).toHaveLength(1)
    expect(screen.getAllByRole('listitem')[0]).toHaveAttribute('aria-current', 'step')
  })

  test('finish button is visible in overview mode', () => {
    render(twoStepOverviewWizardWithButtons)

    expect(screen.getByRole('button', { name: /finish/i })).toBeVisible()
  })

  test('next and previous buttons are hidden in overview mode', () => {
    render(twoStepOverviewWizardWithButtons)

    expect(screen.queryByRole('button', { name: /next step/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /previous step/i })).not.toBeInTheDocument()
  })
})
