/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import FormString from '@/form/components/forms/FormString.vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const validators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const spec: FormSpec.String = {
  type: 'string',
  title: 'fooTitle',
  help: 'fooHelp',
  label: 'fooLabel',
  i18n_base: { required: 'required' },
  validators: validators,
  input_hint: 'fooInputHint',
  autocompleter: null,
  field_size: 'SMALL'
}

test('FormString renders value', () => {
  render(FormString, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })

  expect(element.value).toBe('fooData')
})

test('FormString updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'fooData',
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  await fireEvent.update(element, 'some_other_value')

  expect(getCurrentData()).toBe('"some_other_value"')
})

test('FormString checks validators', async () => {
  render(FormString, {
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

test('FormString renders backend validation messages', async () => {
  render(FormString, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: [
        {
          location: [],
          message: 'Backend error message',
          invalid_value: 'some_invalid_value'
        }
      ]
    }
  })

  await screen.findByText('Backend error message')
  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  expect(element.value).toBe('some_invalid_value')
})

test('FormString displays required', async () => {
  render(FormString, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  screen.getByText('(required)')
})

test('FormString with autocompleter loads value', async () => {
  render(FormString, {
    props: {
      spec: {
        type: 'string',
        title: '',
        help: '',
        validators: [],
        label: 'ut_label',
        input_hint: '',
        field_size: 'MEDIUM',
        autocompleter: {
          data: {
            ident: 'config_hostname',
            params: {
              show_independent_of_context: true,
              strict: true,
              escape_regex: true,
              world: 'world',
              context: {}
            }
          },
          fetch_method: 'ajax_vs_autocomplete'
        },
        i18n_base: {
          required: 'required'
        }
      },
      data: 'some value',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'ut_label' })
  await waitFor(() => {
    expect(element.textContent).toBe('some value')
  })
})
