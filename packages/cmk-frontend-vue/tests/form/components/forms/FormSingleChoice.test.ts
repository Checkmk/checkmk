/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import FormSingleChoice from '@/form/components/forms/FormSingleChoice.vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const spec: FormSpec.SingleChoice = {
  type: 'single_choice',
  title: 'fooTitle',
  input_hint: 'some input hint',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  no_elements_text: 'no_text',
  elements: [
    { name: 'choice1', title: 'Choice 1' },
    { name: 'choice2', title: 'Choice 2' }
  ],
  label: 'fooLabel',
  frozen: false,
  validators: []
}

test('FormSingleChoice renders value', () => {
  render(FormSingleChoice, {
    props: {
      spec,
      data: 'choice1',
      backendValidation: []
    }
  })

  const element = screen.getByLabelText<HTMLInputElement>('fooLabel')

  expect(element).toHaveAccessibleName('fooLabel')
  expect(element).toHaveTextContent('Choice 1')
})

test('FormSingleChoice renders something when noting is selected', () => {
  render(FormSingleChoice, {
    props: {
      spec,
      data: null,
      backendValidation: []
    }
  })

  const element = screen.getByLabelText<HTMLInputElement>('fooLabel')

  expect(element).toHaveAccessibleName('fooLabel')
  expect(element).toHaveTextContent('some input hint (required)')
})

test('FormSingleChoice updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'choice1',
    backendValidation: []
  })

  const element = screen.getByLabelText<HTMLInputElement>('fooLabel')
  await fireEvent.click(element)
  await fireEvent.click(screen.getByText('Choice 2'))

  expect(getCurrentData()).toBe('"choice2"')
})

test('FormSingleChoice renders backend validation messages', async () => {
  render(FormSingleChoice, {
    props: {
      spec,
      data: 'choice1',
      backendValidation: [
        {
          location: [],
          message: 'Backend error message',
          invalid_value: ''
        }
      ]
    }
  })

  await screen.findByText('Backend error message')
})
