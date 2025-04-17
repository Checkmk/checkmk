/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormDualListChoiceComponent from '@/form/components/forms/FormDualListChoice.vue'

const spec: FormSpec.DualListChoice = {
  type: 'dual_list_choice',
  title: 'fooTitle',
  help: 'fooHelp',
  elements: [
    { name: 'choice1', title: 'Choice 1' },
    { name: 'choice2', title: 'Choice 2' },
    { name: 'choice3', title: 'Choice 3' },
    { name: 'choice4', title: 'Choice 4' }
  ],
  i18n: {
    add_all: 'Add all',
    remove_all: 'Remove all',
    add: 'Add',
    remove: 'Remove',
    available_options: 'Available options',
    selected_options: 'Selected options',
    selected: 'Selected',
    no_elements_available: 'No elements available',
    no_elements_selected: 'No elements selected',
    autocompleter_loading: 'Loading',
    search_selected_options: 'i18n search selected options',
    search_available_options: 'i18n search available options',
    and_x_more: 'and %s more'
  },
  validators: [],
  show_toggle_all: false
}

describe('FormDualListChoice', () => {
  test('renders value', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [
          { name: 'choice1', title: 'Choice 1' },
          { name: 'choice3', title: 'Choice 3' },
          { name: 'choice4', title: 'Choice 4' }
        ],
        backendValidation: []
      }
    })

    // check active elements
    const activeElement = screen.getByRole<HTMLSelectElement>('listbox', {
      name: 'Selected options'
    })
    expect(activeElement.options.length).equal(3)

    // check inactive elements
    const inactiveElement = screen.getByRole<HTMLSelectElement>('listbox', {
      name: 'Available options'
    })
    expect(inactiveElement.options.length).equal(1)

    const choice3 = screen.getByRole<HTMLSelectElement>('option', { name: 'Choice 3' })
    await fireEvent.dblClick(choice3)
    expect(inactiveElement.options.length).equal(2)
  })

  test('filter choices', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [
          { name: 'choice1', title: 'Choice 1' },
          { name: 'choice3', title: 'Choice 3' },
          { name: 'choice4', title: 'Choice 4' }
        ],
        backendValidation: []
      }
    })

    const filterActiveElements = screen.getByRole('textbox', {
      name: 'i18n search selected options'
    })
    await fireEvent.update(filterActiveElements, 'Choice 1')
    expect(
      screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' }).options.length
    ).equal(1)

    const filterInactiveElements = screen.getByRole('textbox', {
      name: 'i18n search available options'
    })

    await fireEvent.update(filterInactiveElements, 'Choice 1')
    expect(screen.getByText('No elements available')).toBeInTheDocument()
  })

  test('add all while filter on available options', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [
          { name: 'choice3', title: 'Choice 3' },
          { name: 'choice4', title: 'Choice 4' }
        ],
        backendValidation: []
      }
    })

    const filterInactiveElements = screen.getByRole('textbox', {
      name: 'i18n search available options'
    })
    await fireEvent.update(filterInactiveElements, 'Choice 1')
    const addAll = screen.getByRole<HTMLButtonElement>('button', { name: 'Add all' })
    await fireEvent.click(addAll)
    expect(
      screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' }).options.length
    ).equal(3)
  })

  test('remove all while filter on selected options', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [
          { name: 'choice1', title: 'Choice 1' },
          { name: 'choice3', title: 'Choice 3' },
          { name: 'choice4', title: 'Choice 4' }
        ],
        backendValidation: []
      }
    })

    const filterActiveElements = screen.getByRole('textbox', {
      name: 'i18n search selected options'
    })
    await fireEvent.update(filterActiveElements, 'Choice 1')
    const removeAll = screen.getByRole<HTMLButtonElement>('button', { name: 'Remove all' })
    await fireEvent.click(removeAll)
    expect(
      screen.getByRole<HTMLSelectElement>('listbox', { name: 'Available options' }).options.length
    ).equal(2)

    expect(screen.getByText('No elements selected')).toBeInTheDocument()
  })

  test('add by double click on available item', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [
          { name: 'choice1', title: 'Choice 1' },
          { name: 'choice3', title: 'Choice 3' },
          { name: 'choice4', title: 'Choice 4' }
        ],
        backendValidation: []
      }
    })

    const choice2 = screen.getByRole<HTMLSelectElement>('option', { name: 'Choice 2' })
    await fireEvent.dblClick(choice2)
    expect(
      screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' }).options.length
    ).equal(4)
  })

  // Marked as fails because the input v-model is not updating the selection in vitest
  test.fails('add by clicking add button having selected item', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [],
        backendValidation: []
      }
    })

    const choice2 = screen.getByRole<HTMLSelectElement>('option', { name: 'Choice 2' })
    await fireEvent.click(choice2)

    const add = screen.getByRole<HTMLButtonElement>('button', { name: 'Add' })
    await fireEvent.click(add)

    expect(
      screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' }).options.length
    ).equal(1)
  })

  test('remove by double click on selected item', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [
          { name: 'choice1', title: 'Choice 1' },
          { name: 'choice3', title: 'Choice 3' },
          { name: 'choice4', title: 'Choice 4' }
        ],
        backendValidation: []
      }
    })

    const choice3 = screen.getByRole<HTMLSelectElement>('option', { name: 'Choice 3' })
    await fireEvent.dblClick(choice3)
    expect(
      screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' }).options.length
    ).equal(2)
  })

  // Marked as fails because the input v-model is not updating the selection in vitest
  test.fails('remove by clicking remove button having selected item', async () => {
    render(FormDualListChoiceComponent, {
      props: {
        spec,
        data: [{ name: 'choice1', title: 'Choice 1' }],
        backendValidation: []
      }
    })

    const choice = screen.getByRole('option', { name: 'Choice 1' })
    await fireEvent.click(choice)

    const remove = screen.getByRole<HTMLButtonElement>('button', { name: 'Remove' })
    await fireEvent.click(remove)

    expect(
      screen.getByRole<HTMLSelectElement>('listbox', { name: 'Available options' }).options.length
    ).equal(0)
  })

  describe('style', () => {
    test('list height must be 200px when there is less than 10 elements', async () => {
      render(FormDualListChoiceComponent, {
        props: {
          spec: {
            ...spec,
            elements: [
              { name: 'choice1', title: 'Choice 1' },
              { name: 'choice2', title: 'Choice 2' },
              { name: 'choice3', title: 'Choice 3' },
              { name: 'choice4', title: 'Choice 4' },
              { name: 'choice5', title: 'Choice 5' },
              { name: 'choice6', title: 'Choice 6' },
              { name: 'choice7', title: 'Choice 7' },
              { name: 'choice8', title: 'Choice 8' },
              { name: 'choice9', title: 'Choice 9' }
            ]
          },
          data: [
            { name: 'choice1', title: 'Choice 1' },
            { name: 'choice3', title: 'Choice 3' },
            { name: 'choice4', title: 'Choice 4' }
          ],
          backendValidation: []
        }
      })

      const list = screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' })
      expect(list.style.height).toBe('200px')
    })

    test('list height must be (11 * 15)px when there is 11 elements', async () => {
      render(FormDualListChoiceComponent, {
        props: {
          spec: {
            ...spec,
            elements: [
              { name: 'choice1', title: 'Choice 1' },
              { name: 'choice2', title: 'Choice 2' },
              { name: 'choice3', title: 'Choice 3' },
              { name: 'choice4', title: 'Choice 4' },
              { name: 'choice5', title: 'Choice 5' },
              { name: 'choice6', title: 'Choice 6' },
              { name: 'choice7', title: 'Choice 7' },
              { name: 'choice8', title: 'Choice 8' },
              { name: 'choice9', title: 'Choice 9' },
              { name: 'choice10', title: 'Choice 10' },
              { name: 'choice11', title: 'Choice 11' }
            ]
          },
          data: [
            { name: 'choice1', title: 'Choice 1' },
            { name: 'choice3', title: 'Choice 3' },
            { name: 'choice4', title: 'Choice 4' }
          ],
          backendValidation: []
        }
      })

      const list = screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' })
      expect(list.style.height).toBe('165px')
    })
    test('list max height must be 400px when there is lots of items', async () => {
      render(FormDualListChoiceComponent, {
        props: {
          spec: {
            ...spec,
            elements: [
              { name: 'choice1', title: 'Choice 1' },
              { name: 'choice2', title: 'Choice 2' },
              { name: 'choice3', title: 'Choice 3' },
              { name: 'choice4', title: 'Choice 4' },
              { name: 'choice5', title: 'Choice 5' },
              { name: 'choice6', title: 'Choice 6' },
              { name: 'choice7', title: 'Choice 7' },
              { name: 'choice8', title: 'Choice 8' },
              { name: 'choice9', title: 'Choice 9' },
              { name: 'choice10', title: 'Choice 10' },
              { name: 'choice11', title: 'Choice 11' },
              { name: 'choice12', title: 'Choice 12' },
              { name: 'choice13', title: 'Choice 13' },
              { name: 'choice14', title: 'Choice 14' },
              { name: 'choice15', title: 'Choice 15' },
              { name: 'choice16', title: 'Choice 16' },
              { name: 'choice17', title: 'Choice 17' },
              { name: 'choice18', title: 'Choice 18' },
              { name: 'choice19', title: 'Choice 19' },
              { name: 'choice20', title: 'Choice 20' },
              { name: 'choice21', title: 'Choice 21' },
              { name: 'choice22', title: 'Choice 22' },
              { name: 'choice23', title: 'Choice 23' },
              { name: 'choice24', title: 'Choice 24' },
              { name: 'choice25', title: 'Choice 25' },
              { name: 'choice26', title: 'Choice 26' },
              { name: 'choice27', title: 'Choice 27' },
              { name: 'choice28', title: 'Choice 28' },
              { name: 'choice29', title: 'Choice 29' },
              { name: 'choice30', title: 'Choice 30' }
            ]
          },
          data: [
            { name: 'choice1', title: 'Choice 1' },
            { name: 'choice3', title: 'Choice 3' },
            { name: 'choice4', title: 'Choice 4' }
          ],
          backendValidation: []
        }
      })
      const list = screen.getByRole<HTMLSelectElement>('listbox', { name: 'Selected options' })
      expect(list.style.height).toBe('400px')
    })
  })
})
