/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormOptionalChoice from '@/form/components/forms/FormOptionalChoice.vue'
import FormEdit from '@/form/components/FormEdit.vue'

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
  render(FormEdit, {
    props: {
      spec,
      data: 42,
      backendValidation: [
        { location: ['parameter_form'], message: 'Backend error message', replacement_value: 23 }
      ]
    }
  })

  await screen.findByText('Backend error message')
})

test('FormOptionalChoice renders own validation message', async () => {
  render(FormOptionalChoice, {
    props: {
      spec,
      data: 42,
      backendValidation: [{ location: [], message: 'Backend error message', replacement_value: 23 }]
    }
  })

  await screen.findByText('Backend error message')
})

test('FormOptionalChoice renders None/null value', async () => {
  render(FormOptionalChoice, {
    props: {
      spec,
      data: null,
      backendValidation: []
    }
  })

  screen.getByRole<HTMLInputElement>('checkbox', { name: 'optional choice label' })
  // expect(within(element).getByRole<HTMLInputElement>('textbox').value).toBe('some value')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormOptionalChoice renders parameter_form(Integer) value', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: 23,
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(element.value).toBe('23')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormOptionalChoice updates validation', async () => {
  const { rerender } = render(FormEdit, {
    props: {
      spec,
      data: 23,
      backendValidation: []
    }
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

test('FormOptionalChoice enables/disables option', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: null,
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('checkbox', { name: 'optional choice label' })
  await fireEvent.click(element)

  const integerElement = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(integerElement.value).toBe('23')

  await fireEvent.click(element)
  expect(screen.queryByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })).toBeNull()
})
