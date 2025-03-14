/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, findByRole, findAllByRole } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import CheckboxListChoice from '@/form/components/forms/FormCheckboxListChoice.vue'

const spec: FormSpec.CheckboxListChoice = {
  type: 'checkbox_list_choice',
  title: 'fooTitle',
  help: 'fooHelp',
  elements: [
    { name: 'choice1', title: 'Choice 1' },
    { name: 'choice2', title: 'Choice 2' },
    { name: 'choice3', title: 'Choice 3' },
    { name: 'choice4', title: 'Choice 4' }
  ],
  validators: [],
  i18n: {
    add: 'i18n add',
    remove: 'i18n remove',
    add_all: 'i18n add_all',
    remove_all: 'i18n remove_all',
    available_options: 'i18n available_options',
    selected_options: 'i18n selected_options',
    selected: 'i18n selected',
    no_elements_available: 'i18n no_elements_available',
    no_elements_selected: 'i18n no_elements_selected',
    autocompleter_loading: 'i18n autocompleter_loading',
    search_selected_options: 'i18n search selected options',
    search_available_options: 'i18n search available options',
    and_x_more: 'i18n and_x_more'
  }
}

test('CmkFormCheckboxListChoice renders value', async () => {
  render(CheckboxListChoice, {
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

  // check that aria attributes are set up correctly:
  const listbox = await screen.findByRole('listbox', { name: 'fooTitle' })

  const choice1Checkbox = await findByRole(
    // each checkbox should be in an option:
    // we check this for the first choice which is expected in the first option
    (await findAllByRole(listbox, 'option'))[0]!,
    'checkbox',
    {
      name: 'Choice 1'
    }
  )
  expect(choice1Checkbox).toBeChecked()

  const choice2Checkbox = await findByRole(listbox, 'checkbox', { name: 'Choice 2' })
  expect(choice2Checkbox).not.toBeChecked()

  const choice3Checkbox = await findByRole(listbox, 'checkbox', { name: 'Choice 3' })
  expect(choice3Checkbox).toBeChecked()

  const choice4Checkbox = await findByRole(listbox, 'checkbox', { name: 'Choice 4' })
  expect(choice4Checkbox).toBeChecked()

  await fireEvent.click(choice2Checkbox)
  expect(choice2Checkbox).toBeChecked()
})
