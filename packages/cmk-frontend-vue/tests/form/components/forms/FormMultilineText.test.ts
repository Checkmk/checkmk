/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'
import FormMultilineText from '@/form/components/forms/FormMultilineText.vue'

const validators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const spec: FormSpec.MultilineText = {
  type: 'multiline_text',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  input_hint: 'fooInputHint',
  label: 'fooLabel',
  macro_support: false,
  monospaced: false
}

test('FormMultilineText renders value', () => {
  render(FormMultilineText, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLTextAreaElement>('textbox', { name: 'fooLabel' })

  expect(element.value).toBe('fooData')
})

test('FormMultilineText updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'fooData',
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  await fireEvent.update(element, 'some_other_value')

  expect(getCurrentData()).toBe('"some_other_value"')
})

test('FormMultilineText checks validators', async () => {
  render(FormMultilineText, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormMultilineText renders backend validation messages', async () => {
  render(FormMultilineText, {
    props: {
      spec,
      data: 'fooData',
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
