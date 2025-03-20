/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, queryByText, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'
import FormEdit from '@/form/components/FormEdit.vue'

const stringValidators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const integerFormSpec: FormSpec.Integer = {
  type: 'integer',
  title: 'nestedIntegerTitle',
  label: 'nestedIntegerLabel',
  help: 'nestedIntegerHelp',
  i18n_base: { required: 'required' },
  validators: [],
  input_hint: null,
  unit: null
}

const stringFormSpec: FormSpec.String = {
  type: 'string',
  title: 'barTitle',
  help: 'barHelp',
  label: null,
  i18n_base: { required: 'required' },
  validators: stringValidators,
  input_hint: '',
  autocompleter: null,
  field_size: 'SMALL'
}

const cascadingSingleChoiceSpec: FormSpec.CascadingSingleChoice = {
  type: 'cascading_single_choice',
  title: 'fooTitle',
  label: 'fooLabel',
  i18n_base: { required: 'required' },
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

const singleChoiceSpec: FormSpec.SingleChoice = {
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

const listCascadingSpec: FormSpec.ListUniqueSelection = {
  type: 'list_unique_selection',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  element_template: cascadingSingleChoiceSpec,
  element_default_value: ['', null],
  add_element_label: 'Add element',
  remove_element_label: 'Remove element',
  no_element_label: 'No element',
  unique_selection_elements: ['stringChoice', 'integerChoice']
}

const listSpec: FormSpec.ListUniqueSelection = {
  type: 'list_unique_selection',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  element_template: singleChoiceSpec,
  element_default_value: '',
  add_element_label: 'Add element',
  remove_element_label: 'Remove element',
  no_element_label: 'No element',
  unique_selection_elements: ['choice1', 'choice2']
}

test('FormListUniqueSelection (CascadingSingleChoice) no add button if selected and both are unique', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: listCascadingSpec,
    data: [['integerChoice', 10]],
    backendValidation: []
  })

  const addElementButton = screen.getByText('Add element')
  await fireEvent.click(addElementButton)
  const singleChoiceElements = screen.getAllByText<HTMLInputElement>('fooLabel')
  expect(singleChoiceElements).toHaveLength(2)
  const secondSingleChoiceElement = singleChoiceElements[1] as HTMLInputElement
  await fireEvent.click(secondSingleChoiceElement)
  await fireEvent.click(screen.getByText('stringChoiceTitle'))
  expect(screen.queryByText('Add element')).toBeNull()
  expect(getCurrentData()).toBe('[["integerChoice",10],["stringChoice","bar"]]')
})

test('FormListUniqueSelection (SingleChoice) no add button if selected and both are unique', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: listSpec,
    data: ['choice1'],
    backendValidation: []
  })

  const addElementButton = screen.getByText('Add element')
  await fireEvent.click(addElementButton)
  const singleChoiceElements = screen.getAllByText<HTMLInputElement>('fooLabel')
  expect(singleChoiceElements).toHaveLength(2)
  const secondSingleChoiceElement = singleChoiceElements[1] as HTMLInputElement
  await fireEvent.click(secondSingleChoiceElement)
  await fireEvent.click(screen.getByText('Choice 2'))
  expect(screen.queryByText('Add element')).toBeNull()
  expect(getCurrentData()).toBe('["choice1","choice2"]')
})

test('FormListUniqueSelection local child validation overwrites backend validation', async () => {
  render(FormEdit, {
    props: {
      spec: listCascadingSpec,
      data: [['stringChoice', 'some value']],
      backendValidation: [
        { location: ['0', '1'], message: 'Backend error message', replacement_value: 'other value' }
      ]
    }
  })

  const textbox = await screen.findByRole<HTMLInputElement>('textbox')
  await fireEvent.update(textbox, '')

  screen.getByText('String length must be between 1 and 20')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormListUniqueSelection unique element only shows once', async () => {
  render(FormEdit, {
    props: {
      spec: listSpec,
      data: ['choice1'],
      backendValidation: []
    }
  })

  const addElementButton = screen.getByText('Add element')
  await fireEvent.click(addElementButton)
  const singleChoiceElements = screen.getAllByText<HTMLInputElement>('fooLabel')
  expect(singleChoiceElements).toHaveLength(2)
  const secondSingleChoiceElement = singleChoiceElements[1] as HTMLInputElement
  await fireEvent.click(secondSingleChoiceElement)
  expect(queryByText(secondSingleChoiceElement, 'Choice 1')).toBeNull()
})

test('FormListUniqueSelection shows backend validation pointing to list', async () => {
  render(FormEdit, {
    props: {
      spec: listSpec,
      data: [],
      backendValidation: [{ location: [], message: 'Backend error message', replacement_value: [] }]
    }
  })
  screen.getByText('Backend error message')
})
