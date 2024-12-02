/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import CheckboxListChoice from '@/form/components/forms/FormCheckboxListChoice.vue'

const spec: FormSpec.CheckboxListChoice = {
  type: 'checkbox_list_choice',
  title: 'fooTitle',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  elements: [
    { name: 'choice1', title: 'Choice 1' },
    { name: 'choice2', title: 'Choice 2' },
    { name: 'choice3', title: 'Choice 3' },
    { name: 'choice4', title: 'Choice 4' }
  ],
  validators: []
}

test('CmkFormCheckboxListChoice renders value', async () => {
  render(CheckboxListChoice, {
    props: {
      spec,
      data: ['choice1', 'choice3', 'choice4'],
      backendValidation: []
    }
  })

  const choice1Checkbox = await screen.findByRole('checkbox', { name: 'Choice 1' })
  expect(choice1Checkbox).toBeChecked()
  const choice2Checkbox = await screen.findByRole('checkbox', { name: 'Choice 2' })
  expect(choice2Checkbox).not.toBeChecked()

  const choice3Checkbox = await screen.findByRole('checkbox', { name: 'Choice 3' })
  expect(choice3Checkbox).toBeChecked()

  const choice4Checkbox = await screen.findByRole('checkbox', { name: 'Choice 4' })
  expect(choice4Checkbox).toBeChecked()

  await fireEvent.click(choice2Checkbox)
  expect(choice2Checkbox).toBeChecked()
})
