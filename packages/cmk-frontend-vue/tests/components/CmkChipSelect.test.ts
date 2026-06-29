/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { h } from 'vue'

import CmkChipSelect from '@/components/CmkChipSelect.vue'

const timeRanges = {
  type: 'fixed' as const,
  suggestions: [
    { title: 'Last hour', name: '1h' },
    { title: 'Last day', name: '1d' }
  ]
}

test('renders the input hint when nothing is selected', () => {
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: null, inputHint: 'More ranges', label: 'time range' }
  })

  const trigger = screen.getByRole('combobox', { name: 'time range' })
  expect(trigger).toHaveTextContent('More ranges')
})

test('renders the selected option title on the trigger', () => {
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: '1d', inputHint: 'More ranges', label: 'time range' }
  })

  expect(screen.getByRole('combobox', { name: 'time range' })).toHaveTextContent('Last day')
})

test('click opens the popup and shows the options', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: null, inputHint: 'More ranges', label: 'time range' }
  })

  await user.click(screen.getByRole('combobox', { name: 'time range' }))

  await screen.findByText('Last hour')
  await screen.findByText('Last day')
})

test('marks the selected option with a checkmark, others without', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: '1d', inputHint: 'More ranges', label: 'time range' }
  })

  await user.click(screen.getByRole('combobox', { name: 'time range' }))

  const selectedRow = await screen.findByRole('option', { name: 'Last day' })
  expect(selectedRow.querySelector('.cmk-suggestions__selected-mark')).not.toBeNull()

  const otherRow = screen.getByRole('option', { name: 'Last hour' })
  expect(otherRow.querySelector('.cmk-suggestions__selected-mark')).toBeNull()
})

test('staticLabel keeps the input hint on the trigger while still marking the selected option', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: {
      options: timeRanges,
      modelValue: '1d',
      inputHint: 'More ranges',
      label: 'time range',
      staticLabel: true
    }
  })

  const trigger = screen.getByRole('combobox', { name: 'time range' })
  expect(trigger).toHaveTextContent('More ranges')
  expect(trigger).not.toHaveTextContent('Last day')

  await user.click(trigger)

  const selectedRow = await screen.findByRole('option', { name: 'Last day' })
  expect(selectedRow.querySelector('.cmk-suggestions__selected-mark')).not.toBeNull()
})

test('selecting an option updates the model and closes the popup', async () => {
  const user = userEvent.setup()
  const { emitted } = render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: null, inputHint: 'More ranges', label: 'time range' }
  })

  await user.click(screen.getByRole('combobox', { name: 'time range' }))
  await user.click(await screen.findByRole('option', { name: 'Last hour' }))

  expect(emitted('update:modelValue')!.at(-1)).toEqual(['1h'])
  await waitFor(() => expect(screen.queryByText('Last day')).toBeNull())
})

test('clicking outside closes the popup', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: null, inputHint: 'More ranges', label: 'time range' }
  })

  await user.click(screen.getByRole('combobox', { name: 'time range' }))
  await screen.findByText('Last hour')

  document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
  await waitFor(() => expect(screen.queryByText('Last hour')).toBeNull())
})

test('Escape closes the popup and restores focus to the trigger', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: null, inputHint: 'More ranges', label: 'time range' }
  })

  const trigger = screen.getByRole('combobox', { name: 'time range' })
  await user.click(trigger)
  await screen.findByText('Last hour')

  await user.keyboard('{Escape}')

  await waitFor(() => expect(screen.queryByText('Last hour')).toBeNull())
  expect(trigger).toHaveFocus()
})

test('disabled trigger does not open the popup', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: {
      options: timeRanges,
      modelValue: null,
      inputHint: 'More ranges',
      label: 'time range',
      disabled: true
    }
  })

  await user.click(screen.getByRole('combobox', { name: 'time range' }))
  expect(screen.queryByText('Last hour')).toBeNull()
})

test('links the trigger to the popup via aria-controls only while open', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: null, inputHint: 'More ranges', label: 'time range' }
  })

  const trigger = screen.getByRole('combobox', { name: 'time range' })
  expect(trigger).not.toHaveAttribute('aria-controls')

  await user.click(trigger)
  const listbox = await screen.findByRole('listbox')
  expect(listbox.id).toBeTruthy()
  expect(trigger).toHaveAttribute('aria-controls', listbox.id)
})

test('does not open when there are no options and no results hint', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: {
      options: { type: 'fixed', suggestions: [] },
      modelValue: null,
      inputHint: 'More ranges',
      label: 'time range'
    }
  })

  await user.click(screen.getByRole('combobox', { name: 'time range' }))
  expect(screen.queryByRole('listbox')).toBeNull()
})

test('forwards the option slot to the suggestion rows', async () => {
  const user = userEvent.setup()
  render(CmkChipSelect, {
    props: { options: timeRanges, modelValue: null, inputHint: 'More ranges', label: 'time range' },
    slots: {
      option: (props: { suggestion: { title: string } }) =>
        h('span', { class: 'custom-option' }, `range:${props.suggestion.title}`)
    }
  })

  await user.click(screen.getByRole('combobox', { name: 'time range' }))
  const row = await screen.findByRole('option', { name: 'Last hour' })
  expect(row.querySelector('.custom-option')?.textContent).toBe('range:Last hour')
})
