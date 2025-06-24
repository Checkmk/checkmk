/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormCascadingSingleChoice from '@/form/components/forms/FormCascadingSingleChoice.vue'
import FormEdit from '@/form/components/FormEdit.vue'
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
  label: 'nestedStringLabel',
  help: 'nestedStringHelp',
  i18n_base: { required: 'required' },
  validators: stringValidators,
  input_hint: 'nestedStringInputHint',
  field_size: 'SMALL',
  autocompleter: null
}

const integerFormSpec: FormSpec.Integer = {
  type: 'integer',
  title: 'nestedIntegerTitle',
  label: 'nestedIntegerLabel',
  i18n_base: { required: 'required' },
  help: 'nestedIntegerHelp',
  validators: [],
  input_hint: null,
  unit: null
}

const spec: FormSpec.CascadingSingleChoice = {
  type: 'cascading_single_choice',
  title: 'fooTitle',
  label: 'fooLabel',
  i18n_base: { required: 'required' },
  layout: 'horizontal',
  help: 'fooHelp',
  validators: [],
  input_hint: '',
  no_elements_text: '',
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

test('FormCascadingSingleChoice displays data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'some_value'],
    backendValidation: []
  })

  screen.getByRole<HTMLInputElement>('combobox', {
    name: 'fooLabel'
  })

  const stringElement = screen.getByRole<HTMLInputElement>('textbox', { name: 'nestedStringLabel' })
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
  await fireEvent.click(element)
  await fireEvent.click(await screen.findByText('integerChoiceTitle'))

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
  await fireEvent.click(element)
  await fireEvent.click(await screen.findByText('integerChoiceTitle'))
  // make sure the default value is propagated
  expect(getCurrentData()).toMatch('["integerChoice",5]')

  // now switch back to the string
  await fireEvent.click(element)
  await fireEvent.click(await screen.findByText('stringChoiceTitle'))

  // now the other value should still be there, not the default value
  expect(getCurrentData()).toMatch('["stringChoice","other_value"]')
})

test('FormCascadingSingleChoice checks validators', async () => {
  render(FormEdit, {
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
          replacement_value: ''
        }
      ]
    }
  })

  await screen.findByText('Backend error message')
})

test('FormCascadingSingleChoice does not poisen the template value', async () => {
  // before this test FormCascadingSingleChoice would use the the default_value by reference.
  // so if you next FormCascadingSingleChoice in a FormList, then all
  // FormCascadingSingleChoice would share the same value, as they all use the
  // very same default value. the problem can also be demonstrated in a simplified form:

  const dictFromSpec: FormSpec.Dictionary = {
    type: 'dictionary',
    title: 'fooTitle',
    help: 'fooHelp',
    i18n_base: { required: 'required' },
    validators: [],
    groups: [],
    additional_static_elements: null,
    no_elements_text: 'no_text',
    elements: [
      {
        name: 'value',
        render_only: false,
        required: false,
        default_value: 'baz',
        parameter_form: stringFormSpec,
        group: null
      }
    ]
  }

  const defaultValue = { value: 'something' }

  const spec: FormSpec.CascadingSingleChoice = {
    type: 'cascading_single_choice',
    title: 'fooTitle',
    label: 'fooLabel',
    i18n_base: { required: 'required' },
    layout: 'horizontal',
    help: 'fooHelp',
    validators: [],
    input_hint: '',
    no_elements_text: '',
    elements: [
      {
        name: 'dictChoice',
        title: 'stringChoiceTitle',
        // the default_value is an object
        default_value: defaultValue,
        parameter_form: dictFromSpec
      }
    ]
  }
  render(FormEdit, {
    props: {
      spec,
      // the current data does not match, so when...
      data: ['null', 'null'],
      backendValidation: []
    }
  })

  // ... chosing only available option, the default value will be used to fill
  // the dictionary with values
  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })
  await fireEvent.click(element)
  await fireEvent.update(await screen.findByText('stringChoiceTitle'))

  // now we change the nested value of said default value
  const stringElement = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(stringElement, 'other_value')

  // but we expect that our local defaultValue is not affected by this change:
  expect(defaultValue).toEqual({ value: 'something' })
})
