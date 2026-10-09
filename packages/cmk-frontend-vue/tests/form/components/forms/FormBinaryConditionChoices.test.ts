/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

import FormBinaryConditionChoices from '@/form/private/forms/FormBinaryConditionChoices/FormBinaryConditionChoices.vue'

const spec: FormSpec.BinaryConditionChoices = {
  type: 'binary_condition_choices',
  title: 'Host labels',
  help: '',
  validators: [
    {
      type: 'length_in_range',
      min_value: 1,
      max_value: null,
      error_message: 'Please add at least one host label.'
    }
  ],
  label: 'Label',
  autocompleter: {
    fetch_method: 'rest_autocomplete',
    data: { ident: 'label', params: { world: 'core', object_type: 'host' } }
  }
}

test('FormBinaryConditionChoices shows backendValidation', () => {
  render(FormBinaryConditionChoices, {
    props: {
      spec,
      data: [],
      backendValidation: [{ location: [], message: 'some message', replacement_value: [] }]
    }
  })

  expect(screen.getByText('some message')).toBeVisible()
})

test('FormBinaryConditionChoices shows the replacement value of backendValidation', async () => {
  const linux: FormSpec.BinaryConditionChoicesGroup = {
    operator: 'and',
    label_group: [{ operator: 'and', label: 'os:linux' }]
  }
  const { rerender } = render(FormBinaryConditionChoices, {
    props: { spec, data: [linux, { operator: 'or', label_group: [] }], backendValidation: [] }
  })

  await rerender({
    backendValidation: [{ location: [], message: 'some message', replacement_value: [linux] }]
  })

  expect(screen.getByText('some message')).toBeVisible()
  expect(screen.getAllByRole('button', { name: 'Remove group' })).toHaveLength(1)
})

test('FormBinaryConditionChoices drops backendValidation once the value is valid', async () => {
  const data: FormSpec.BinaryConditionChoicesValue = [
    { operator: 'and', label_group: [{ operator: 'and', label: 'os:linux' }] },
    { operator: 'or', label_group: [] }
  ]
  render(FormBinaryConditionChoices, {
    props: {
      spec,
      data,
      backendValidation: [{ location: [], message: 'some message', replacement_value: data }]
    }
  })

  await fireEvent.click(screen.getAllByRole('button', { name: 'Remove group' })[1]!)

  expect(screen.queryByText('some message')).toBeNull()
})

test('FormBinaryConditionChoices validates groups without labels like the backend', async () => {
  render(FormBinaryConditionChoices, {
    props: { spec, data: [], backendValidation: [] }
  })

  await fireEvent.click(screen.getByRole('button', { name: 'Add to condition' }))

  expect(screen.getByText('Please add at least one host label.')).toBeVisible()
})
