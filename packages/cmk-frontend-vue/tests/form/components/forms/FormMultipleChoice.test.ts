/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import CmkFormMultipleChoice from '@/form/components/forms/FormMultipleChoice.vue'

const spec: FormSpec.MultipleChoice = {
  type: 'multiple_choice',
  title: 'fooTitle',
  help: 'fooHelp',
  elements: [
    { name: 'choice1', title: 'Choice 1' },
    { name: 'choice2', title: 'Choice 2' },
    { name: 'choice3', title: 'Choice 3' },
    { name: 'choice4', title: 'Choice 4' }
  ],
  validators: [],
  show_toggle_all: false
}

test('CmkFormMultipleChoice renders value', async () => {
  render(CmkFormMultipleChoice, {
    props: {
      spec,
      data: ['choice1', 'choice3', 'choice4'],
      backendValidation: []
    }
  })

  // check active elements
  const activeElement = screen.getByRole<HTMLSelectElement>('listbox', { name: 'active' })
  expect(activeElement.options.length).equal(3)

  // check inactive elements
  const inactiveElement = screen.getByRole<HTMLSelectElement>('listbox', { name: 'available' })
  expect(inactiveElement.options.length).equal(1)

  const choice3 = screen.getByRole<HTMLSelectElement>('option', { name: 'Choice 3' })
  await fireEvent.dblClick(choice3)
  expect(inactiveElement.options.length).equal(2)
})
