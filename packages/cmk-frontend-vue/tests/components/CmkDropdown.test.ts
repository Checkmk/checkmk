/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'
import type { ComponentProps } from 'vue-component-type-helpers'

import CmkDropdown from '@/components/CmkDropdown'
import { ErrorResponse, Response } from '@/components/CmkSuggestions'

test('dropdown shows options', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'fixed',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })

  await fireEvent.click(dropdown)

  await screen.findByText('Option 1')
})

test('dropdown marks selectedOptions as selected', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'fixed',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Preselected Option', name: 'preselected_option' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: 'preselected_option',
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })

  await fireEvent.click(dropdown)

  await expect((await screen.findAllByRole('option'))[1]).toHaveClass('selected')
})

test('dropdown updates selecedOption', async () => {
  let selectedOption: string | null = ''
  const props = {
    options: {
      type: 'fixed' as const,
      suggestions: [
        { title: 'Option 1', name: 'option1' },
        { title: 'Option 2', name: 'option2' }
      ]
    },
    selectedOption: null,
    inputHint: 'Select an option',
    showFilter: true,
    'onUpdate:selectedOption': (option: string | null) => {
      selectedOption = option
    },
    label: 'some aria label'
  }
  render(CmkDropdown, { props })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)

  const option1 = await screen.findByRole('option', { name: 'Option 1' })
  await fireEvent.click(option1)

  expect(selectedOption).toBe('option1')
})

test('dropdown shows and hides options', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)

  // Dropdown is open and options are visible
  await screen.findByText('Option 2')

  await fireEvent.click(screen.getByText('Option 1'))

  expect(screen.queryByText('Option 2')).toBeNull()
})

test('dropdown changes label if options change', async () => {
  const testComponent = defineComponent({
    components: { CmkDropdown },
    setup() {
      const options = ref<ComponentProps<typeof CmkDropdown>['options']>({
        type: 'fixed',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      })
      const selectedOption = ref<string | null>('option3')
      return { options, selectedOption }
    },
    template: `
      <button @click="options = {
        type: 'fixed',
        suggestions: [
          { title: 'Option 3', name: 'option3' },
          { title: 'Option 4', name: 'option4' }
        ]
      }">Change Options</button>
      <CmkDropdown
        :options="options"
        :selected-option="selectedOption"
        input-hint="Select an option"
        label="some aria label"
      />
    `
  })

  render(testComponent)

  await userEvent.click(screen.getByRole('button', { name: 'Change Options' }))

  await screen.findByLabelText('Option 3')
})

test('dropdown resets label if option is reset', async () => {
  const testComponent = defineComponent({
    components: { CmkDropdown },
    setup() {
      const selectedOption = ref<string | null>('option1')
      return { selectedOption }
    },
    template: `
      <button @click="selectedOption = null">Reset</button>
      <CmkDropdown
        v-model:selected-option="selectedOption"
        :options="{
          type: 'fixed',
          suggestions: [
            { title: 'Option 1', name: 'option1' },
            { title: 'Option 2', name: 'option2' }
          ]
        }"
        input-hint="Select an option"
        label="some aria label"
      />
    `
  })

  render(testComponent)

  await userEvent.click(screen.getByRole('button', { name: 'Reset' }))

  // Input hint is shown
  await screen.findByLabelText('Select an option')
})

test('dropdown handles race condition when resetting value', async () => {
  let resolveQuery: ((value: Response) => void) | null = null

  const response = new Response([
    {
      name: 'value1',
      title: 'Value 1 Title'
    }
  ])

  const querySuggestions = vi.fn((_) => {
    return new Promise((resolve) => {
      resolveQuery = resolve
    })
  })

  render(
    defineComponent({
      components: { CmkDropdown },
      setup() {
        const selectedOption = ref<string | null>(null)
        return { selectedOption, querySuggestions }
      },
      template: `
      <CmkDropdown
        v-model:selected-option="selectedOption"
        :options="{ type: 'callback-filtered', querySuggestions }"
        input-hint="Select an option"
        label="some aria label"
      />
      <button @click="selectedOption = 'value1'">Set Value</button>
      <button @click="selectedOption = null">Reset Value</button>
    `
    })
  )

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })

  // 1. Set value to 'value1'. This triggers querySuggestions which waits to be resolved.
  await fireEvent.click(screen.getByText('Set Value'))
  // 2. Reset value to null. This updates button label to input hint immediately.
  await fireEvent.click(screen.getByText('Reset Value'))

  // Verify it is currently showing the hint (because null update was fast/sync)
  await screen.findByLabelText('Select an option')

  // 3. Resolve the query for 'value1'.
  await waitFor(() => {
    expect(resolveQuery).not.toBeNull()
    resolveQuery!(response)
  })

  // Wait a bit to ensure any pending promises resolve
  await new Promise((resolve) => setTimeout(resolve, 0))

  // 4. Verify it still shows the hint, NOT the resolved title for 'value1'.
  expect(dropdown).toHaveTextContent('Select an option')
})

test('dropdown hides after clicking already selected option', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'fixed',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: 'option1',
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)

  // Dropdown is open and options are visible
  await screen.findByText('Option 2')

  await fireEvent.click(screen.getByRole('option', { name: 'Option 1' }))

  expect(screen.queryByText('Option 2')).toBeNull()
})

test.each([{ showFilter: true }, { showFilter: false }])(
  'dropdown updates selecedOption selected via keyboard with showFilter=$showFilter',
  async ({ showFilter }) => {
    let selectedOption: string | null = ''
    render(CmkDropdown, {
      props: {
        options: {
          type: showFilter ? 'fixed' : 'filtered',
          suggestions: [
            { title: 'Option 1', name: 'option1' },
            { title: 'Option 2', name: 'option2' }
          ]
        },
        selectedOption: null,
        inputHint: 'Select an option',
        'onUpdate:selectedOption': (option: string | null) => {
          selectedOption = option
        },
        label: 'some aria label'
      }
    })
    await fireEvent.click(screen.getByRole('combobox', { name: 'some aria label' }))

    await userEvent.keyboard('[ArrowDown][Enter]')

    expect(selectedOption).toBe('option2')
  }
)

test('dropdown option selection via keyboard wraps', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: {
        type: 'fixed',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      },
      label: 'some aria label'
    }
  })
  await fireEvent.click(screen.getByRole('combobox', { name: 'some aria label' }))

  await userEvent.keyboard('[ArrowUp][Enter]')

  expect(selectedOption).toBe('option2')
})

test('dropdown option keyboard selection with filtering wraps', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [
          { title: 'Bar', name: 'bar' },
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' },
          { title: 'Foo', name: 'foo' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      },
      label: 'some aria label'
    }
  })
  await fireEvent.click(screen.getByRole('combobox', { name: 'some aria label' }))

  await userEvent.keyboard('opt[ArrowUp][Enter]')

  expect(selectedOption).toBe('option2')
})

test('dropdown keyboard can handle empty dropdown', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })
  await fireEvent.click(screen.getByRole('combobox', { name: 'some aria label' }))

  await userEvent.keyboard('dadada[ArrowUp]')
})

test('dropdown keyboard can handle selection filtered away dropdown', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'aaaaa', name: 'aaaaa' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })
  await fireEvent.click(screen.getByRole('combobox', { name: 'some aria label' }))

  await userEvent.keyboard('[ArrowDown]')
  await userEvent.keyboard('option')
  await userEvent.keyboard('[ArrowUp]')
})

test('dropdown option immediate focus and filtering', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      },
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)

  await userEvent.keyboard('2[Enter]')
  expect(selectedOption).toBe('option2')

  await fireEvent.click(dropdown)
  await userEvent.keyboard('2[Backspace][Enter]')
  expect(selectedOption).toBe('option1')
})

test('dropdown shows required if required is passed', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      required: true,
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  expect(dropdown.textContent).toMatch(/option.*required/)
})

test('dropdown does not show required if required is not passed', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [
          { title: 'Option 1', name: 'option1' },
          { title: 'Option 2', name: 'option2' }
        ]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  expect(dropdown.textContent).toBe('Select an option')
})

test('dropdown still clickable if only option is already selected', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [{ title: 'Option 1', name: 'option1' }]
      },
      selectedOption: 'option1',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)

  await screen.findByRole('option', { name: 'Option 1' })
})

test('dropdown clickable if only one option is available', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'filtered',
        suggestions: [{ title: 'Option 1', name: 'option1' }]
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)

  await screen.findByText('Option 1')
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
          :options="{type: 'filtered', suggestions: [
            { title: 'Option 1', name: 'option1' },
            { title: 'Option 2', name: 'option2' }
          ]}"
          label="some aria label in template"
          input-hint="Select an option"
          @update:selected-option="$emit('update:selectedOption', $event)"
        />
        <input data-testid="next-input" type="text" />
      </div>
    `
  })

  const { emitted } = render(testComponent)

  const nextInput = screen.getByTestId('next-input')
  const dropdown = screen.getByRole('combobox', { name: 'some aria label in template' })
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

test('dropdown with callback and freeform element in first place still selects correctly', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (query) => {
          const first = []
          if (query !== '') {
            first.push({ name: query, title: query })
          }
          return new Response([
            ...first,
            { name: 'one', title: 'one' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ])
        }
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'some aria label',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)
  const input = screen.getByRole('textbox', { name: 'filter' })
  await screen.findByText('four') // make sure suggestions are loaded
  await fireEvent.update(input, 'ut_something')
  await fireEvent.click(await screen.findByText('three'))
  await waitFor(() => expect(selectedOption).toBe('three'))
})

test('dropdown with callback and unselectable suggestion shows title', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          return new Response([
            { name: null, title: 'unselectable' },
            { name: 'one', title: 'one' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ])
        }
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'dropdown-label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'dropdown-label' })
  await fireEvent.click(dropdown)
  await screen.findByText('unselectable')
})

test('dropdown with callback doesnt call callback unnecessarily', async () => {
  let selectedOption: string = 'one'
  const callbackDummy = vi.fn()
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          callbackDummy()
          return new Response([
            { name: 'one', title: '1' },
            { name: 'two', title: '2' },
            { name: 'three', title: '3' },
            { name: 'four', title: '4' }
          ])
        }
      },
      selectedOption,
      inputHint: 'Select an option',
      label: 'dropdown-label',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option!
      }
    }
  })

  // Getting the title calls the callback once
  expect(callbackDummy).toHaveBeenCalledTimes(1)

  const dropdown = screen.getByRole('combobox', { name: 'dropdown-label' })
  await fireEvent.click(dropdown)

  // Opening the dropdown calls the callback again to get all suggestions
  expect(callbackDummy).toHaveBeenCalledTimes(2)

  await userEvent.keyboard('[ArrowDown][Enter]')
  expect(selectedOption).toBe('two')

  // Selecting an option does not call the callback again
  expect(callbackDummy).toHaveBeenCalledTimes(2)
})

test('dropdown with callback and unselectable selects first selectable suggestion', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          return new Response([
            { name: null, title: 'unselectable' },
            { name: 'one', title: 'one' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ])
        }
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'dropdown-label',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'dropdown-label' })
  await fireEvent.click(dropdown)

  await userEvent.keyboard('[Enter]')
  expect(selectedOption).toBe('one')
})

test('dropdown with callback and unselectable selects wraps up', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          return new Response([
            { name: null, title: 'unselectable' },
            { name: 'one', title: 'one' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ])
        }
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'dropdown-label',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'dropdown-label' })
  await fireEvent.click(dropdown)

  await userEvent.keyboard('[ArrowUp][Enter]')
  expect(selectedOption).toBe('four')
})

test('dropdown with callback skips unselectable with keyboard', async () => {
  let selectedOption: string | null = ''
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          return new Response([
            { name: 'one', title: 'one' },
            { name: null, title: 'unselectable' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ])
        }
      },
      selectedOption: null,
      inputHint: 'Select an option',
      label: 'dropdown-label',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'dropdown-label' })
  await fireEvent.click(dropdown)

  await userEvent.keyboard('[ArrowDown][Enter]')
  expect(selectedOption).toBe('three')
})

test('dropdown unselectable is unselectable', async () => {
  let selectedOption: string | null = 'one'
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          return new Response([
            { name: 'one', title: 'one' },
            { name: null, title: 'unselectable' },
            { name: 'three', title: 'three' },
            { name: 'four', title: 'four' }
          ])
        }
      },
      selectedOption,
      inputHint: 'Select an option',
      label: 'dropdown-label',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'dropdown-label' })
  await fireEvent.click(dropdown)

  const unselectable = await screen.findByText('unselectable')
  await fireEvent.click(unselectable)

  expect(selectedOption).toBe('one')
  expect(screen.getByText('unselectable')).toBeInTheDocument()
})

test('dropdown with callback-filtered shows error message when callback returns ErrorResponse', async () => {
  const errorMessage = 'Failed to load suggestions from backend'
  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          return new ErrorResponse(errorMessage)
        }
      },
      selectedOption: 'invalid_value',
      inputHint: 'Select an option',
      label: 'dropdown-label'
    }
  })

  await screen.findByText(errorMessage)

  expect(screen.getByRole('combobox', { name: 'dropdown-label' })).toHaveTextContent(
    'invalid_value'
  )
})

test('dropdown with callback-filtered clears error message after successful selection', async () => {
  const errorMessage = 'Failed to load suggestions'
  let callCount = 0
  let selectedOption: string | null = 'invalid_value'

  render(CmkDropdown, {
    props: {
      options: {
        type: 'callback-filtered',
        querySuggestions: async (_) => {
          callCount++
          if (callCount === 1) {
            return new ErrorResponse(errorMessage)
          }
          return new Response([
            { name: 'one', title: 'one' },
            { name: 'two', title: 'two' }
          ])
        }
      },
      selectedOption,
      inputHint: 'Select an option',
      label: 'dropdown-label',
      'onUpdate:selectedOption': (option: string | null) => {
        selectedOption = option
      }
    }
  })

  await screen.findByText(errorMessage)

  const dropdown = screen.getByRole('combobox', { name: 'dropdown-label' })
  await fireEvent.click(dropdown)

  const option = await screen.findByText('one')
  await fireEvent.click(option)

  await waitFor(() => {
    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument()
  })

  expect(selectedOption).toBe('one')
})
