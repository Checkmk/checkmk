/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import {
  type WizardContext,
  wizardContextProvider
} from 'cmk-ui-library/components/CmkWizard/utils.ts'
import { afterEach, expect, test, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import NameStep from '@/mode-alerts/steps/NameStep.vue'
import { type AlertModel, emptyAlert } from '@/mode-alerts/types'

import { MAIN_FOLDER } from './conditions-spec'

afterEach(() => {
  cleanup()
})

function renderStep(alert: Partial<AlertModel> = {}) {
  const model = ref<AlertModel>({ ...emptyAlert({ folder_path: MAIN_FOLDER }), ...alert })
  const navigation = {
    next: vi.fn<() => void>(),
    prev: vi.fn<() => void>(),
    goto: vi.fn<(index: number) => void>()
  }
  const context: WizardContext = {
    mode: () => 'guided',
    isSelected: () => true,
    navigation
  }
  const wrapper = defineComponent({
    components: { NameStep },
    setup() {
      return { model }
    },
    template: `<NameStep v-model="model" :index="1" :is-completed="() => false" />`
  })
  render(wrapper, {
    global: { provide: { [wizardContextProvider as symbol]: context } }
  })
  return { model, navigation }
}

test('errors are not shown before the first attempt to continue', () => {
  renderStep()

  expect(screen.queryByText('An alert name is required')).not.toBeInTheDocument()
})

test('a missing alert name blocks navigation with a required error', async () => {
  const { navigation } = renderStep()

  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => {
    expect(screen.getByText('An alert name is required')).toBeInTheDocument()
  })
  expect(navigation.next).not.toHaveBeenCalled()
})

test('a named alert continues to the next step', async () => {
  const { model, navigation } = renderStep()

  await userEvent.type(screen.getByRole('textbox', { name: /Alert name/ }), 'Latency too high')
  await userEvent.click(screen.getByRole('button', { name: /next step/i }))

  await waitFor(() => expect(navigation.next).toHaveBeenCalled())
  expect(model.value.name).toBe('Latency too high')
})
