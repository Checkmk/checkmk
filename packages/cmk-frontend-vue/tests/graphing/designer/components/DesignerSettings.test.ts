/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import type { CustomGraphOptions } from '@/graphing/designer/api'
import DesignerSettings from '@/graphing/designer/components/DesignerSettings.vue'

// CmkSlideIn uses Radix-Vue DialogPortal, which doesn't work in jsdom.
vi.mock('cmk-ui-library/components/CmkSlideIn/CmkSlideIn.vue', () => ({
  default: defineComponent({
    name: 'CmkSlideIn',
    setup(_, { slots }) {
      return () => h('div', { 'data-testid': 'slide-in' }, slots.default?.())
    }
  })
}))

function autoOptions(): CustomGraphOptions {
  return {
    unit: { type: 'first_entry_with_unit' },
    explicit_vertical_range: { type: 'auto' },
    omit_zero_metrics: false
  }
}

function renderDesignerSettings(graphOptions: CustomGraphOptions = autoOptions()) {
  return render(DesignerSettings, { props: { open: true, graphOptions } })
}

async function selectOption(comboboxName: string, optionName: string): Promise<void> {
  await fireEvent.click(screen.getByRole('combobox', { name: comboboxName }))
  await fireEvent.click(await screen.findByRole('option', { name: optionName }))
}

test('renders the settings heading and fields reflecting the supplied options', () => {
  renderDesignerSettings()

  expect(screen.getByRole('heading', { name: 'Custom graph settings' })).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Unit' })).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Explicit range' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Show zero values' })).toBeChecked()
})

describe('closing', () => {
  test('clicking Cancel closes the slide-in without emitting updateSettings', async () => {
    const { emitted } = renderDesignerSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(emitted()['update:open']).toEqual([[false]])
    expect(emitted()['updateSettings']).toBeUndefined()
  })

  test('clicking the close icon closes the slide-in', async () => {
    const { emitted } = renderDesignerSettings()

    await fireEvent.click(screen.getByTestId('icon-x-close-button'))

    expect(emitted()['update:open']).toEqual([[false]])
  })
})

describe('accepting', () => {
  test('emits updateSettings with the unchanged options when nothing was edited', async () => {
    const { emitted } = renderDesignerSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    expect(emitted()['updateSettings']).toEqual([[autoOptions()]])
  })

  test('emits updateSettings with edited values', async () => {
    const { emitted } = renderDesignerSettings()

    await fireEvent.click(screen.getByRole('checkbox', { name: 'Show zero values' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    expect(emitted()['updateSettings']).toEqual([[{ ...autoOptions(), omit_zero_metrics: true }]])
  })
})

describe('validation', () => {
  test('blocks accepting invalid rounding digits and shows the error', async () => {
    const { emitted } = renderDesignerSettings()

    await selectOption('Unit', 'Custom')
    await fireEvent.update(screen.getByRole('spinbutton', { name: 'Rounding digits' }), '-1')
    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    expect(
      screen.getByText('The number of digits for rounding must be a non-negative integer')
    ).toBeInTheDocument()
    expect(emitted()['updateSettings']).toBeUndefined()
  })

  test('blocks accepting an invalid vertical range and shows both errors', async () => {
    const { emitted } = renderDesignerSettings()

    await selectOption('Explicit range', 'Explicit range')
    await fireEvent.update(screen.getByRole('spinbutton', { name: 'Lower limit' }), '5')
    await fireEvent.update(screen.getByRole('spinbutton', { name: 'Upper limit' }), '5')
    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    expect(
      screen.getByText('The lower limit must be less than the upper limit')
    ).toBeInTheDocument()
    expect(
      screen.getByText('The upper limit must be greater than the lower limit')
    ).toBeInTheDocument()
    expect(emitted()['updateSettings']).toBeUndefined()
  })

  test('accepting succeeds and clears the errors once the range is corrected', async () => {
    const { emitted } = renderDesignerSettings()

    await selectOption('Explicit range', 'Explicit range')
    await fireEvent.update(screen.getByRole('spinbutton', { name: 'Lower limit' }), '5')
    await fireEvent.update(screen.getByRole('spinbutton', { name: 'Upper limit' }), '5')
    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))
    expect(screen.getAllByRole('alert')).toHaveLength(2)

    await fireEvent.update(screen.getByRole('spinbutton', { name: 'Upper limit' }), '10')
    await fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(emitted()['updateSettings']).toEqual([
      [{ ...autoOptions(), explicit_vertical_range: { type: 'fixed', lower: 5, upper: 10 } }]
    ])
  })
})
