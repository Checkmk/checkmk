/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormPassword from '@/form/components/forms/FormPassword.vue'
import { renderFormWithData } from '../cmk-form-helper'

const validators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: null,
    error_message: 'Min length must be 1'
  }
]
const spec: FormSpec.Password = {
  type: 'password',
  title: 'fooTitle',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  validators: validators,
  password_store_choices: [
    {
      password_id: 'pw_id0',
      name: 'first_password'
    },
    {
      password_id: 'pw_id1',
      name: 'second_password'
    }
  ],
  i18n: {
    choose_password_type: 'i18n choose_password_type',
    choose_password_from_store: 'i18n choose_password_from_store',
    explicit_password: 'explicit_password_i18n',
    password_store: 'password_store_i18n',
    no_password_store_choices: 'no_password_store_choices_i18n',
    password_choice_invalid: 'password_choice_invalid_i18n'
  }
}

test('FormPassword renders validation message', async () => {
  render(FormPassword, {
    props: {
      spec,
      data: ['explicit_password', '', '', true],
      backendValidation: [{ location: [], message: 'Invalid password', replacement_value: '' }]
    }
  })

  await screen.findByText('Invalid password')
})

test('FormPassword user input', async () => {
  render(FormPassword, {
    props: {
      spec,
      data: ['explicit_password', '', '', true],
      backendValidation: []
    }
  })
  const element = screen.getByLabelText<HTMLInputElement>('explicit password')
  await fireEvent.update(element, '')
  screen.getByText('Min length must be 1')
  await fireEvent.update(element, '23')
  expect(screen.queryByText('Min length must be 1')).toBeNull()
})

test('FormPassword updates validation but dont touch value', async () => {
  const { rerender, getCurrentData } = renderFormWithData({
    spec,
    data: ['explicit_password', '', '', true],
    backendValidation: []
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['explicit_password', '', 'some_password', false],
    backendValidation: [
      {
        location: [],
        message: 'Backend error message',
        replacement_value: ''
      }
    ]
  })

  screen.getByText('Backend error message')
  expect(getCurrentData()).toBe('["explicit_password","","some_password",false]')
})

test('FormPassword selected first password store choice if present', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['explicit_password', '', '', true],
    backendValidation: []
  })

  const element = screen.getByRole<HTMLSelectElement>('combobox', {
    name: 'i18n choose_password_type'
  })
  await fireEvent.click(element)
  await fireEvent.click(await screen.findByText('password_store_i18n'))

  expect(getCurrentData()).toBe('["stored_password","pw_id0","",false]')
})
