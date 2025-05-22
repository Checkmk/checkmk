/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import CmkDropdown from '@/components/CmkDropdown.vue'
import { Response } from '@/components/suggestions'
import userEvent from '@testing-library/user-event'
import { render, screen, fireEvent, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

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

test('dropdown truncates center of very long label', async () => {
  render(CmkDropdown, {
    props: {
      options: {
        type: 'fixed',
        suggestions: [
          {
            title: 'AaaaaaaaaaaaaaaaaaaaaaaaAbbbbbbbbbbbbCcccccccccccccccccccccccC',
            name: 'option1'
          }
        ]
      },
      selectedOption: 'option1',
      inputHint: 'Select an option',
      label: 'some aria label'
    }
  })

  expect(
    await screen.findByText('AaaaaaaaaaaaaaaaaaaaaaaaA...CcccccccccccccccccccccccC')
  ).toBeInTheDocument()
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
  const { rerender } = render(CmkDropdown, { props })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  await fireEvent.click(dropdown)

  const option1 = await screen.findByText('Option 1')
  await fireEvent.click(option1)

  expect(selectedOption).toBe('option1')

  // Check that dropdown now shows the selected option
  await rerender({ ...props, selectedOption })
  await waitFor(() => screen.getByText('Option 1'))
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

test('dropdown shows required if requiredText is passed', async () => {
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
      requiredText: 'required',
      label: 'some aria label'
    }
  })

  const dropdown = screen.getByRole('combobox', { name: 'some aria label' })
  expect(dropdown.textContent).toBe('Select an option (required)')
})

test('dropdown does not show required if requiredText is not passed', async () => {
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

  const dropdown = await screen.findByText('Option 1')
  await fireEvent.click(dropdown)

  // show it twice: once as current value and second time as the only value to choose.
  await waitFor(() => expect(screen.queryAllByText('Option 1')).toHaveLength(2))
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
