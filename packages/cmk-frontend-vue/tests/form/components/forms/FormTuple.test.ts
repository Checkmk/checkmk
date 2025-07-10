/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormEdit from '@/form/components/FormEdit.vue'

const stringSpec1: FormSpec.String = {
  type: 'string',
  title: 'firstFooTitle',
  help: 'firstFooHelp',
  label: null,
  i18n_base: { required: 'required' },
  validators: [],
  input_hint: 'firstFooInputHint',
  autocompleter: null,
  field_size: 'SMALL'
}

const stringSpec2: FormSpec.String = {
  type: 'string',
  title: 'secondFooTitle',
  help: 'secondFooHelp',
  label: null,
  i18n_base: { required: 'required' },
  validators: [],
  input_hint: 'secondFooInputHint',
  autocompleter: null,
  field_size: 'SMALL'
}

const spec: FormSpec.Tuple = {
  type: 'tuple',
  title: 'barTitle',
  help: 'barHelp',
  layout: 'horizontal',
  show_titles: true,
  validators: [],
  elements: [stringSpec1, stringSpec2]
}

test('FormTuple renders element validation message', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: ['foo', 'bar'],
      backendValidation: [
        { location: ['0'], message: 'Backend error message', replacement_value: '23' }
      ]
    }
  })

  await screen.findByText('Backend error message')
})

test('FormTuple renders own validation message', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: ['foo', 'bar'],
      backendValidation: [{ location: [], message: 'Backend error message', replacement_value: '' }]
    }
  })

  screen.getByText('Backend error message')
})

test('FormTuple renders value', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: ['some value', 'other value'],
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'firstFooTitle' })
  expect(element.value).toBe('some value')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormTuple renders updated validation', async () => {
  const { rerender } = render(FormEdit, {
    props: {
      spec,
      data: ['some value', 'other value'],
      backendValidation: []
    }
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['changed value', 'other value'],
    backendValidation: [
      { location: ['0'], message: 'Backend error message', replacement_value: 'new_error_value' }
    ]
  })

  screen.getByText('Backend error message')

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'firstFooTitle' })
  expect(element.value).toBe('new_error_value')
})
