/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormFolder from '@/form/components/forms/FormFolder.vue'

const validators: FormSpec.Validator[] = [
  {
    type: 'match_regex',
    regex:
      '^(?:[~\\\\/]?[-_ a-zA-Z0-9.]{1,32}(?:[~\\\\/][-_ a-zA-Z0-9.]{1,32})*[~\\\\/]?|[~\\\\/]?)$',
    error_message: 'Invalid characters in fooTitle'
  }
]
const spec: FormSpec.Folder = {
  type: 'folder',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  input_hint: 'fooInputHint'
}

test('FormFolder renders validation message', async () => {
  render(FormFolder, {
    props: {
      spec,
      data: 'bla',
      backendValidation: [{ location: [], message: 'Backend error message', invalid_value: 'bla' }]
    }
  })

  await screen.findByText('Backend error message')
})

test('FormFolder renders prefix "Main/"', () => {
  render(FormFolder, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  screen.getByText<HTMLSpanElement>('Main/')
})

test('FormFolder renders input hint', () => {
  render(FormFolder, {
    props: {
      spec,
      data: '',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')

  expect(element.placeholder).toBe('fooInputHint')
})

test('FormFolder renders value', () => {
  render(FormFolder, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')

  expect(element.value).toBe('fooData')
})
