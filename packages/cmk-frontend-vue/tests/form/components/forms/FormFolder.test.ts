/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { ref, watch } from 'vue'
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
const autocompleter: FormSpec.Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'wato_folder_choices',
    params: {}
  }
}
const spec: FormSpec.Folder = {
  type: 'folder',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  input_hint: 'fooInputHint',
  autocompleter: autocompleter,
  allow_new_folder_path: false
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

test('FormFolder renders value', async () => {
  render(FormFolder, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')

  await waitFor(() => {
    expect(element.value).toBe('fooData')
  })
})

vi.mock('@/form/components/utils/autocompleter', () => ({
  setupAutocompleter: vi.fn(() => {
    const input = ref('')
    const output = ref()

    watch(input, async (newVal) => {
      if (newVal) {
        await new Promise((resolve) => setTimeout(resolve, 100))
        output.value = {
          choices: [
            ['@main', 'Main'],
            ['folder1', 'folder1'],
            ['folder2', 'folder2']
          ].filter((item) => item[0]?.includes(newVal))
        }
      }
    })

    return { input, output }
  })
}))

test('FormFolder ignores "Main" folder', async () => {
  render(FormFolder, {
    props: {
      spec,
      data: '',
      backendValidation: []
    }
  })

  const input = screen.getByPlaceholderText('fooInputHint')
  await fireEvent.update(input, 'fo')

  await waitFor(() => {
    expect(screen.queryByText('Main')).not.toBeInTheDocument()
  })
})

test('FormFolder does not allow new folder path', async () => {
  render(FormFolder, {
    props: {
      spec,
      data: '',
      backendValidation: []
    }
  })

  const input = screen.getByPlaceholderText('fooInputHint')
  await fireEvent.update(input, 'fo')

  await waitFor(() => {
    expect(screen.getByText('folder1')).toBeInTheDocument()
    expect(screen.getByText('folder2')).toBeInTheDocument()
    expect(screen.queryByText('fo')).not.toBeInTheDocument()
  })
})

test('FormFolder allows new folder path', async () => {
  const testSpec = {
    ...spec,
    allow_new_folder_path: true
  }
  render(FormFolder, {
    props: {
      spec: testSpec,
      data: '',
      backendValidation: []
    }
  })

  const input = screen.getByPlaceholderText('fooInputHint')
  await fireEvent.update(input, 'fo')

  await waitFor(() => {
    expect(screen.getByText('folder1')).toBeInTheDocument()
    expect(screen.getByText('folder2')).toBeInTheDocument()
    expect(screen.getByText('fo')).toBeInTheDocument()
  })
})
