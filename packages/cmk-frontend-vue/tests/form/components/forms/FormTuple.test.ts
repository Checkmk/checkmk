/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, within } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import FormTuple from '@/form/components/forms/FormTuple.vue'

const stringSpec1: FormSpec.String = {
  type: 'string',
  title: 'firstFooTitle',
  help: 'firstFooHelp',
  validators: [],
  input_hint: 'firstFooInputHint',
  autocompleter: null,
  field_size: 'SMALL'
}

const stringSpec2: FormSpec.String = {
  type: 'string',
  title: 'secondFooTitle',
  help: 'secondFooHelp',
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
  render(FormTuple, {
    props: {
      spec,
      data: ['foo', 'bar'],
      backendValidation: [
        { location: ['0'], message: 'Backend error message', invalid_value: '23' }
      ]
    }
  })

  await screen.findByText('Backend error message')
})

test('FormTuple renders own validation message', async () => {
  render(FormTuple, {
    props: {
      spec,
      data: ['foo', 'bar'],
      backendValidation: [{ location: [], message: 'Backend error message', invalid_value: '' }]
    }
  })

  screen.getByText('Backend error message')
})

test('FormTuple renders value', async () => {
  render(FormTuple, {
    props: {
      spec,
      data: ['some value', 'other value'],
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('cell', { name: /FirstFooTitle/ })
  expect(within(element).getByRole<HTMLInputElement>('textbox').value).toBe('some value')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormTuple renders updated validation', async () => {
  const { rerender } = render(FormTuple, {
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
      { location: ['0'], message: 'Backend error message', invalid_value: 'new_error_value' }
    ]
  })

  screen.getByText('Backend error message')

  const element = screen.getByRole<HTMLInputElement>('cell', { name: /FirstFooTitle/ })
  expect(within(element).getByRole<HTMLInputElement>('textbox').value).toBe('new_error_value')
})
