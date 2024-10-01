/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import FormPassword from '@/form/components/forms/FormPassword.vue'

const validators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    error_message: 'Min length must be 1'
  }
]
const spec: FormSpec.Password = {
  type: 'password',
  title: 'fooTitle',
  help: 'fooHelp',
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
    explicit_password: 'explicit_password',
    password_store: 'password_store',
    no_password_store_choices: 'no_password_store_choices',
    password_choice_invalid: 'password_choice_invalid'
  }
}

test('FormPassword renders validation message', async () => {
  render(FormPassword, {
    props: {
      spec,
      data: ['explicit_password', '', '', true],
      backendValidation: [{ location: [], message: 'Invalid password', invalid_value: '' }]
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
  const { rerender } = render(FormPassword, {
    props: {
      spec,
      data: ['explicit_password', '', '', true],
      backendValidation: []
    }
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['explicit_password', '', 'some_password', false],
    backendValidation: [
      {
        location: [],
        message: 'Backend error message',
        invalid_value: ''
      }
    ]
  })

  screen.getByText('Backend error message')
  const element = screen.getByLabelText<HTMLInputElement>('explicit password')
  expect(element.value).toBe('some_password')
})
