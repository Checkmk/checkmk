/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import FormFloat from '@/form/components/forms/FormFloat.vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const validators: FormSpec.Validator[] = [
  {
    type: 'number_in_range',
    min_value: 1,
    max_value: 100,
    error_message: 'Value must be between 1 and 100'
  }
]

const spec: FormSpec.Float = {
  type: 'float',
  title: 'fooTitle',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  validators: validators,
  label: 'fooLabel',
  unit: 'fooUnit',
  input_hint: 'fooInputHint'
}

test('FormFloat renders value', () => {
  render(FormFloat, {
    props: {
      spec,
      data: 42.5,
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })

  expect(element.value).toBe('42.5')
})

test('FormFloat renders required', () => {
  render(FormFloat, {
    props: {
      spec,
      data: 42.5,
      backendValidation: []
    }
  })

  screen.getByText(/required/)
})

test('FormFloat updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 42.5,
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  await fireEvent.update(element, '23.1')

  expect(getCurrentData()).toMatch('23.1')
})

test('FormFloat checks validators', async () => {
  render(FormFloat, {
    props: {
      spec,
      data: 42.5,
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  await fireEvent.update(element, '0.1')

  screen.getByText('Value must be between 1 and 100')
})

test('FormFloat renders backend validation messages', async () => {
  render(FormFloat, {
    props: {
      spec,
      data: 42.0,
      backendValidation: [
        { location: [], message: 'Backend error message', replacement_value: 12.5 }
      ]
    }
  })

  await screen.findByText('Backend error message')
  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(element.value).toBe('12.5')
})
