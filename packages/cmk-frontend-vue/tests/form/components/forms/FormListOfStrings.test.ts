/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

import { renderForm } from '../cmk-form-helper'

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
  title: 'barTitle',
  help: 'barHelp',
  label: null,
  validators: stringValidators,
  input_hint: '',
  autocompleter: null,
  field_size: 'SMALL'
}

const spec: FormSpec.ListOfStrings = {
  type: 'list_of_strings',
  title: 'fooTitle',
  help: 'fooHelp',
  layout: 'horizontal',
  validators: stringValidators,
  string_spec: stringFormSpec,
  string_default_value: 'baz'
}

test('FormListOfStrings renders backend validation messages', async () => {
  await renderForm({
    spec,
    data: [],
    backendValidation: [{ location: [], message: 'Backend error message', replacement_value: '' }]
  })

  screen.getByText('Backend error message')
})

test('FormListOfStrings updated backend child validation shows validation error', async () => {
  const { rerender } = await renderForm({
    spec,
    data: ['some value'],
    backendValidation: []
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['some value'],
    backendValidation: [
      { location: ['0'], message: 'Backend error message', replacement_value: 'other value' }
    ]
  })

  screen.getByText('Backend error message')
  const textboxes = screen.getAllByRole<HTMLInputElement>('textbox')
  expect(textboxes[0]!.value).toBe('other value')
})

test('FormListOfStrings local child validation overwrites backend validation', async () => {
  await renderForm({
    spec,
    data: ['some value'],
    backendValidation: [
      { location: ['0'], message: 'Backend error message', replacement_value: 'other value' }
    ]
  })

  const textboxes = await screen.getAllByRole<HTMLInputElement>('textbox')
  await fireEvent.update(textboxes[0]!, '')

  screen.getByText('String length must be between 1 and 20')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormListOfStrings shows frontend validation on existing element', async () => {
  ;(
    await renderForm({
      spec,
      data: ['some_value'],
      backendValidation: []
    })
  ).emitted('select')

  const textboxes = await screen.getAllByRole<HTMLInputElement>('textbox')
  await fireEvent.update(textboxes[0]!, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormListOfStrings check autoextend', async () => {
  await renderForm({
    spec: spec,
    data: [],
    backendValidation: []
  })

  let elements = await screen.getAllByRole('textbox')
  expect(elements).toHaveLength(1)

  await fireEvent.update(elements[0]!, '1234')
  elements = await screen.getAllByRole('textbox')
  expect(elements).toHaveLength(2)
})

test('FormListOfStrings paste with leading/trailing semicolons splits correctly', async () => {
  await renderForm({
    spec: spec,
    data: [],
    backendValidation: []
  })

  const elements = screen.getAllByRole<HTMLInputElement>('textbox')
  expect(elements).toHaveLength(1)

  const pasteData = ';;value1;value2;;value3;;'
  await fireEvent.paste(elements[0]!, {
    clipboardData: {
      getData: () => pasteData
    }
  })

  const updatedElements = screen.getAllByRole<HTMLInputElement>('textbox')
  expect(updatedElements).toHaveLength(4)
  expect(updatedElements[0]!.value).toBe('value1')
  expect(updatedElements[1]!.value).toBe('value2')
  expect(updatedElements[2]!.value).toBe('value3')
  expect(updatedElements[3]!.value).toBe('')
})

test('FormListOfStrings paste with leading/trailing whitespace trims correctly', async () => {
  await renderForm({
    spec: spec,
    data: [],
    backendValidation: []
  })

  const elements = screen.getAllByRole<HTMLInputElement>('textbox')
  expect(elements).toHaveLength(1)

  const pasteData = '\tvalue1 ; value2\n  ;value3\r\n'
  await fireEvent.paste(elements[0]!, {
    clipboardData: {
      getData: () => pasteData
    }
  })

  const updatedElements = screen.getAllByRole<HTMLInputElement>('textbox')
  expect(updatedElements).toHaveLength(4)
  expect(updatedElements[0]!.value).toBe('value1')
  expect(updatedElements[1]!.value).toBe('value2')
  expect(updatedElements[2]!.value).toBe('value3')
  expect(updatedElements[3]!.value).toBe('')
})
