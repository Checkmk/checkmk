/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

import { renderForm } from '../cmk-form-helper'

const validators: FormSpec.Validator[] = [
  {
    type: 'number_in_range',
    min_value: 1,
    max_value: 100,
    error_message: 'Value must be between 1 and 100'
  }
]
const integerSpec: FormSpec.Integer = {
  type: 'integer',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  label: 'fooLabel',
  unit: 'fooUnit',
  input_hint: 'fooInputHint'
}

const spec: FormSpec.OptionalChoice = {
  type: 'optional_choice',
  title: 'optional choice title',
  help: 'optional choice help',
  i18n: {
    label: 'optional choice label',
    none_label: 'optional choice none label'
  },
  validators: [],
  parameter_form: integerSpec,
  parameter_form_default_value: 23
}

test('FormOptionalChoice renders element validation message', async () => {
  await renderForm({
    spec,
    data: 42,
    backendValidation: [
      { location: ['parameter_form'], message: 'Backend error message', replacement_value: 23 }
    ]
  })

  await screen.findByText('Backend error message')
})

test('FormOptionalChoice renders own validation message', async () => {
  await renderForm({
    spec,
    data: 42,
    backendValidation: [{ location: [], message: 'Backend error message', replacement_value: 23 }]
  })

  await screen.findByText('Backend error message')
})

test('FormOptionalChoice renders None/null value', async () => {
  await renderForm({
    spec,
    data: null,
    backendValidation: []
  })

  screen.getByRole<HTMLInputElement>('checkbox', { name: 'optional choice label' })
  // expect(within(element).getByRole<HTMLInputElement>('textbox').value).toBe('some value')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormOptionalChoice renders parameter_form(Integer) value', async () => {
  await renderForm({
    spec,
    data: 23,
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(element.value).toBe('23')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormOptionalChoice updates validation', async () => {
  const { rerender } = await renderForm({
    spec,
    data: 23,
    backendValidation: []
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: 24,
    backendValidation: [
      {
        location: ['parameter_form'],
        message: 'Backend error message',
        replacement_value: 66
      }
    ]
  })

  screen.getByText('Backend error message')

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(element.value).toBe('66')
})

test('FormOptionalChoice with title delegates help rendering to parent', async () => {
  await renderForm({
    spec,
    data: null,
    backendValidation: []
  })

  expect(screen.queryAllByRole('button', { name: '?' })).toHaveLength(0)
})

test('FormOptionalChoice as dictionary element renders help only once', async () => {
  const dictionarySpec: FormSpec.Dictionary = {
    type: 'dictionary',
    title: 'dictionary title',
    help: '',
    validators: [],
    groups: [],
    additional_static_elements: null,
    no_elements_text: '',
    elements: [
      {
        name: 'optional',
        render_only: false,
        required: true,
        default_value: null,
        parameter_form: spec,
        group: null
      }
    ]
  }
  await renderForm({
    spec: dictionarySpec,
    data: { optional: null },
    backendValidation: []
  })

  expect(screen.getAllByRole('button', { name: '?' })).toHaveLength(1)
})

test('FormOptionalChoice without title renders own help', async () => {
  await renderForm({
    spec: { ...spec, title: '' },
    data: null,
    backendValidation: []
  })

  expect(screen.getAllByRole('button', { name: '?' })).toHaveLength(1)
})

test('FormOptionalChoice shows required tag of revealed element without label', async () => {
  const labelLessIntegerSpec: FormSpec.Integer = { ...integerSpec, label: null }
  const specWithLabelLessInteger: FormSpec.OptionalChoice = {
    ...spec,
    parameter_form: labelLessIntegerSpec
  }
  await renderForm({
    spec: specWithLabelLessInteger,
    data: null,
    backendValidation: []
  })

  expect(screen.queryByText('(required)')).toBeNull()

  const element = screen.getByRole<HTMLInputElement>('checkbox', { name: 'optional choice label' })
  await fireEvent.click(element)

  expect(screen.getAllByText('(required)')).toHaveLength(1)
})

test('FormOptionalChoice renders required tag only once for element with label', async () => {
  await renderForm({
    spec,
    data: 23,
    backendValidation: []
  })

  expect(screen.getAllByText('(required)')).toHaveLength(1)
})

test('FormOptionalChoice enables/disables option', async () => {
  await renderForm({
    spec,
    data: null,
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('checkbox', { name: 'optional choice label' })
  await fireEvent.click(element)

  const integerElement = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(integerElement.value).toBe('23')

  await fireEvent.click(element)
  expect(screen.queryByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })).toBeNull()
})
