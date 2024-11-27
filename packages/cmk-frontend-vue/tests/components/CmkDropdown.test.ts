/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import CmkDropdown from '@/components/CmkDropdown.vue'
import userEvent from '@testing-library/user-event'
import { render, screen, fireEvent, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

test('dropdown shows options', async () => {
  render(CmkDropdown, {
    props: {
      options: [
        { title: 'Option 1', name: 'option1' },
        { title: 'Option 2', name: 'option2' }
      ],
      selectedOption: null,
      inputHint: 'Select an option',
      showFilter: true
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'Select an option' })

  await fireEvent.click(dropdown)

  screen.getByText('Option 1')
})

test('dropdown updates selecedOption', async () => {
  let selectedOption: string | null = ''
  const props = {
    options: [
      { title: 'Option 1', name: 'option1' },
      { title: 'Option 2', name: 'option2' }
    ],
    selectedOption: null,
    inputHint: 'Select an option',
    showFilter: true,
    'onUpdate:selectedOption': (option: string | null) => {
      selectedOption = option
    }
  }
  const { rerender } = render(CmkDropdown, { props })

  const dropdown = screen.getByRole('combobox', { name: 'Select an option' })
  await fireEvent.click(dropdown)

  const option1 = screen.getByText('Option 1')
  await fireEvent.click(option1)

  expect(selectedOption).toBe('option1')

  // Check that dropdown now shows the selected option
  rerender({ ...props, selectedOption })
  await waitFor(() => screen.getByText('Option 1'))
})

test('dropdown shows and hides options', async () => {
  render(CmkDropdown, {
    props: {
      options: [
        { title: 'Option 1', name: 'option1' },
        { title: 'Option 2', name: 'option2' }
      ],
      showFilter: true,
      selectedOption: null,
      inputHint: 'Select an option'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'Select an option' })
  await fireEvent.click(dropdown)

  // Dropdown is open and options are visible
  screen.getByText('Option 2')

  await fireEvent.click(screen.getByText('Option 1'))

  expect(screen.queryByText('Option 2')).toBeNull()
})

test('dropdown updates selecedOption selected via keyboard', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: [
        { title: 'Option 1', name: 'option1' },
        { title: 'Option 2', name: 'option2' }
      ],
      showFilter: true,
      selectedOption: null,
      inputHint: 'Select an option',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })
  await fireEvent.click(screen.getByRole('combobox', { name: 'Select an option' }))

  await userEvent.keyboard('[ArrowDown][Enter]')

  expect(selectedOption).toBe('option2')
})

test('dropdown option selection via keyboard wraps', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: [
        { title: 'Option 1', name: 'option1' },
        { title: 'Option 2', name: 'option2' }
      ],
      showFilter: true,
      selectedOption: null,
      inputHint: 'Select an option',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })
  await fireEvent.click(screen.getByRole('combobox', { name: 'Select an option' }))

  await userEvent.keyboard('[ArrowUp][Enter]')

  expect(selectedOption).toBe('option2')
})

test('dropdown option immediate focus and filtering', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: [
        { title: 'Option 1', name: 'option1' },
        { title: 'Option 2', name: 'option2' }
      ],
      showFilter: true,
      selectedOption: null,
      inputHint: 'Select an option',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'Select an option' })
  await fireEvent.click(dropdown)

  await userEvent.keyboard('2[Enter]')
  expect(selectedOption).toBe('option2')

  await fireEvent.click(dropdown)
  await userEvent.keyboard('2[Backspace][Enter]')
  expect(selectedOption).toBe('option1')
})

test('dropdown doesnt interfere with tab order', async () => {
  const testComponent = defineComponent({
    components: { CmkDropdown },
    setup() {
      const selectedOption = ref(null)
      return { selectedOption }
    },
    template: `
      <div>
        <CmkDropdown
          :selected-option="selectedOption"
          :options="[
            { title: 'Option 1', name: 'option1' },
            { title: 'Option 2', name: 'option2' }
          ]"
          :show-filter="true"
          input-hint="Select an option"
          @update:selected-option="$emit('update:selectedOption', $event)"
        />
        <input data-testid="next-input" type="text" />
      </div>
    `
  })

  const { emitted } = render(testComponent)

  const nextInput = screen.getByTestId('next-input')
  const dropdown = screen.getByRole('combobox', { name: 'Select an option' })
  dropdown.focus()

  // Open, select option2 by arrow keys and submit
  await userEvent.keyboard('[Space][ArrowDown][Enter]')
  expect(emitted('update:selectedOption')).toEqual([['option2']])
  expect(document.activeElement).toBe(dropdown)

  // Tab to the next element
  await userEvent.tab()
  expect(document.activeElement).toBe(nextInput)

  // Tab back, open & tab
  await userEvent.tab({ shift: true })
  expect(document.activeElement).toBe(dropdown)
  await userEvent.keyboard('[Space]')
  await userEvent.tab()

  // We remain on dropdown
  expect(document.activeElement).toBe(dropdown)
})
