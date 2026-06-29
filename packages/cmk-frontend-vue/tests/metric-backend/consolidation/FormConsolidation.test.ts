/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import FormConsolidation from '@/metric-backend/consolidation/FormConsolidation.vue'
import type { ConsolidationModel } from '@/metric-backend/consolidation/types'

function renderWidget(initial: Partial<ConsolidationModel> = {}) {
  const model = ref<ConsolidationModel>({
    type: 'sum',
    function: 'rate',
    params: {},
    lookbackSeconds: 300,
    ...initial
  })
  const wrapper = defineComponent({
    components: { FormConsolidation },
    setup() {
      return { model }
    },
    template: `
      <div>
        <button type="button">outside</button>
        <FormConsolidation v-model="model" />
      </div>
    `
  })
  render(wrapper)
  return { model }
}

function chip() {
  return screen.getByRole('button', { name: /Edit consolidation/ })
}

test('the collapsed chip summarises the configuration', () => {
  renderWidget()
  expect(chip()).toHaveTextContent('[sum]')
  expect(chip()).toHaveTextContent('rate')
  expect(chip()).toHaveTextContent('5 m')
})

test('clicking the chip expands the controls in place', async () => {
  renderWidget()
  await userEvent.click(chip())

  expect(screen.queryByRole('button', { name: /Edit consolidation/ })).toBeNull()
  expect(screen.getByRole('group', { name: 'Lookback' })).toBeVisible()
  expect(screen.getByText('over last')).toBeVisible()
})

test('the lookback editor offers minutes and seconds but not hours', async () => {
  renderWidget()
  await userEvent.click(chip())

  expect(screen.getByLabelText('Lookback Minutes')).toBeVisible()
  expect(screen.getByLabelText('Lookback Seconds')).toBeVisible()
  expect(screen.queryByLabelText('Lookback Hours')).toBeNull()
})

test('Escape collapses back to the chip', async () => {
  renderWidget()
  await userEvent.click(chip())

  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(chip()).toBeVisible())
})

test('clicking outside collapses back to the chip', async () => {
  renderWidget()
  await userEvent.click(chip())

  await userEvent.click(screen.getByRole('button', { name: 'outside' }))

  await waitFor(() => expect(chip()).toBeVisible())
})

test('editing the lookback updates the chip once collapsed', async () => {
  const { model } = renderWidget()
  await userEvent.click(chip())

  // 300s shows as 5 minutes; clear it and enter 1 minute → 60s.
  const minutes = screen.getByLabelText('Lookback Minutes')
  await userEvent.clear(minutes)
  await userEvent.type(minutes, '1')
  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(model.value.lookbackSeconds).toBe(60))
  expect(chip()).toHaveTextContent('1 m')
})
