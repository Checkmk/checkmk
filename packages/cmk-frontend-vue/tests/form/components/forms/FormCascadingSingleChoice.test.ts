/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import FormCascadingSingleChoice from '@/form/components/forms/FormCascadingSingleChoice.vue'
import { renderFormWithData } from '../cmk-form-helper'

const stringValidators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const stringFormSpec: FormSpec.String = {
  type: 'string',
  title: 'nestedStringTitle',
  help: 'nestedStringHelp',
  validators: stringValidators,
  input_hint: ''
}

const integerFormSpec: FormSpec.Integer = {
  type: 'integer',
  title: 'nestedIntegerTitle',
  label: 'nestedIntegerLabel',
  help: 'nestedIntegerHelp',
  validators: [],
  input_hint: ''
}

const spec: FormSpec.CascadingSingleChoice = {
  type: 'cascading_single_choice',
  title: 'fooTitle',
  label: 'fooLabel',
  layout: 'horizontal',
  help: 'fooHelp',
  validators: [],
  input_hint: '',
  elements: [
    {
      name: 'stringChoice',
      title: 'stringChoiceTitle',
      default_value: 'bar',
      parameter_form: stringFormSpec
    },
    {
      name: 'integerChoice',
      title: 'integerChoiceTitle',
      default_value: 5,
      parameter_form: integerFormSpec
    }
  ]
}

test('FormCascadingSingleChoice displays data', () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'some_value'],
    backendValidation: []
  })

  const selectElement = screen.getByRole<HTMLInputElement>('combobox', { name: /fooLabel/i })
  expect(selectElement.value).toBe('stringChoice')

  const stringElement = screen.getByRole<HTMLInputElement>('textbox', {})
  expect(stringElement.value).toBe('some_value')

  expect(getCurrentData()).toMatch('["stringChoice","some_value"]')
})

test('FormDictionary updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'some_value'],
    backendValidation: []
  })

  const stringElement = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(stringElement, 'other_value')

  expect(getCurrentData()).toMatch('["stringChoice","other_value"]')
})

test('FormCascadingSingleChoice sets default on switch', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'some_value'],
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })
  await fireEvent.update(element, 'integerChoice')

  const integerElement = screen.getByRole<HTMLInputElement>('spinbutton', {
    name: 'nestedIntegerLabel'
  })
  expect(integerElement.value).toBe('5')

  expect(getCurrentData()).toMatch('["integerChoice",5]')
})

test('FormCascadingSingleChoice keeps previously inserted data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'bar'],
    backendValidation: []
  })

  // make sure the non default text input value is actually there
  expect(getCurrentData()).toMatch('["stringChoice","bar"]')

  // change to a non default value
  const stringElement = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(stringElement, 'other_value')
  // make sure the input in the string field is propagated
  expect(getCurrentData()).toMatch('["stringChoice","other_value"]')

  // switch to integer input
  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })
  await fireEvent.update(element, 'integerChoice')
  // make sure the default value is propagated
  expect(getCurrentData()).toMatch('["integerChoice",5]')

  // now switch back to the string
  await fireEvent.update(element, 'stringChoice')

  // now the other value should still be there, not the default value
  expect(getCurrentData()).toMatch('["stringChoice","other_value"]')
})

test('FormCascadingSingleChoice checks validators', async () => {
  render(FormCascadingSingleChoice, {
    props: {
      spec,
      data: ['stringChoice', 'some_value'],
      backendValidation: []
    }
  })

  const stringElement = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(stringElement, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormCascadingSingleChoice renders backend validation messages', async () => {
  render(FormCascadingSingleChoice, {
    props: {
      spec,
      data: ['stringChoice', 'some_value'],
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
