/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'

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
  i18n_base: { required: 'required' },
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
  render(FormEdit, {
    props: {
      spec,
      data: [],
      backendValidation: [{ location: [], message: 'Backend error message', invalid_value: '' }]
    }
  })

  screen.getByText('Backend error message')
})

test('FormListOfStrings updated backend child validation shows validation error', async () => {
  const { rerender } = render(FormEdit, {
    props: {
      spec,
      data: ['some value'],
      backendValidation: []
    }
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['some value'],
    backendValidation: [
      { location: ['0'], message: 'Backend error message', invalid_value: 'other value' }
    ]
  })

  screen.getByText('Backend error message')
  const textboxes = screen.getAllByRole<HTMLInputElement>('textbox')
  expect(textboxes[0]!.value).toBe('other value')
})

test('FormListOfStrings local child validation overwrites backend validation', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: ['some value'],
      backendValidation: [
        { location: ['0'], message: 'Backend error message', invalid_value: 'other value' }
      ]
    }
  })

  const textboxes = await screen.getAllByRole<HTMLInputElement>('textbox')
  await fireEvent.update(textboxes[0]!, '')

  screen.getByText('String length must be between 1 and 20')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormListOfStrings shows frontend validation on existing element', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: ['some_value'],
      backendValidation: []
    }
  }).emitted('select')

  const textboxes = await screen.getAllByRole<HTMLInputElement>('textbox')
  await fireEvent.update(textboxes[0]!, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormListOfStrings check autoextend', async () => {
  render(FormEdit, {
    props: {
      spec: spec,
      data: [],
      backendValidation: []
    }
  })

  let elements = await screen.getAllByRole('textbox')
  expect(elements).toHaveLength(1)

  await fireEvent.update(elements[0]!, '1234')
  elements = await screen.getAllByRole('textbox')
  expect(elements).toHaveLength(2)
})
