/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { Regex } from 'cmk-shared-typing/typescript/vue_formspec_components'

import FormRegex from '@/form/private/forms/FormRegex/FormRegex.vue'

const regexSpec: Regex = {
  type: 'regex',
  title: '',
  help: 'help',
  validators: [],
  label: '',
  input_type: 'regex',
  no_results_hint: 'No results found',
  autocompleter: {
    data: {
      ident: 'config_hostname',
      params: {
        show_independent_of_context: true,
        strict: true,
        input_hint: 'Type to search...'
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  }
}
const textSpec: Regex = {
  type: 'regex',
  title: '',
  help: 'help',
  validators: [],
  label: '',
  input_type: 'text',
  no_results_hint: 'No results found',
  autocompleter: {
    data: {
      ident: 'config_hostname',
      params: {
        show_independent_of_context: true,
        strict: true,
        input_hint: 'Type to search...'
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  }
}

test('renders RegexTextInput with correct props', () => {
  render(FormRegex, {
    props: {
      spec: regexSpec,
      backendValidation: [],
      data: ''
    }
  })
  const input = screen.getByPlaceholderText('Enter regex (pattern match)')
  expect(input).toBeInTheDocument()
})
test('toggle button state is regex when input_type is "regex"', () => {
  const specWithRegex = {
    ...regexSpec,
    input_type: 'regex'
  }
  render(FormRegex, {
    props: {
      spec: specWithRegex,
      backendValidation: [],
      data: ''
    }
  })
  const toggle = screen.getByRole('button', { name: 'Regex' })
  expect(toggle).toBeInTheDocument()
  expect(toggle).toHaveAttribute('aria-pressed', 'true')
})

test('toggle button state is text when input_type is "text"', async () => {
  const specWithText = {
    ...textSpec,
    input_type: 'text'
  }
  render(FormRegex, {
    props: {
      spec: specWithText,
      backendValidation: [],
      data: ''
    }
  })
  const toggle = screen.getByRole('button', { name: 'Text' })
  await userEvent.click(toggle)
  expect(toggle).toBeInTheDocument()
  expect(toggle).toHaveAttribute('aria-pressed', 'true')

  const input = screen.getByPlaceholderText('Enter plain text (single match)')
  expect(input).toBeInTheDocument()
})

test('shows suggestions when input is focused', async () => {
  render(FormRegex, {
    props: {
      spec: regexSpec,
      backendValidation: [],
      data: ''
    }
  })

  const input = screen.getByRole('textbox')
  await userEvent.click(input)

  const items = await screen.findAllByRole('listitem')
  expect(items.length).toBeGreaterThan(0)
})

test('shows suggestions when input is focused and regex toggle is active', async () => {
  render(FormRegex, {
    props: {
      spec: regexSpec,
      backendValidation: [],
      data: ''
    }
  })

  const input = screen.getByRole('textbox')
  await userEvent.click(input)

  const regexSuggestions = screen.getByText('No results found')
  expect(regexSuggestions).toBeInTheDocument()
})

test('shows suggestions dropdown when input is focused', async () => {
  render(FormRegex, {
    props: {
      spec: regexSpec,
      backendValidation: [],
      data: ''
    }
  })

  const input = screen.getByRole('textbox')
  await userEvent.click(input)

  expect(input).toHaveAttribute('aria-expanded', 'true')
})

test('displays no results hint when no suggestions are found', async () => {
  render(FormRegex, {
    props: {
      spec: regexSpec,
      backendValidation: [],
      data: ''
    }
  })

  const input = screen.getByRole('textbox')
  await userEvent.click(input)

  await screen.findByText('No results found')
})
