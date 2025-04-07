/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Metric, Validator } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { Response } from '@/components/suggestions'
import FormMetric from '@/form/components/forms/FormMetric.vue'
import { fireEvent, render, screen } from '@testing-library/vue'
import { vi } from 'vitest'
import { renderFormWithData } from '../cmk-form-helper'

vi.mock(import('@/form/components/utils/autocompleter'), async (importOriginal) => {
  const mod = await importOriginal() // type is inferred
  return {
    ...mod,
    fetchSuggestions: vi.fn(async (_config: unknown, value: string) => {
      await new Promise((resolve) => setTimeout(resolve, 100))
      return new Response(
        [
          { name: 'choicea', title: 'Choice A' },
          { name: 'choiceb', title: 'Choice B' }
        ].filter((item) => item.name.includes(value))
      )
    })
  }
})

const validators: Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const spec: Metric = {
  type: 'metric',
  title: 'Metric',
  help: '',
  validators: validators,
  i18n_base: {
    required: 'required'
  },
  label: null,
  input_hint: '(Select metric)',
  field_size: 'MEDIUM',
  autocompleter: {
    data: {
      ident: 'monitored_metrics',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: false
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  },
  service_filter_autocompleter: {
    data: {
      ident: 'monitored_service_description',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: false
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  },
  host_filter_autocompleter: {
    data: {
      ident: 'config_hostname',
      params: {
        show_independent_of_context: true,
        strict: true,
        escape_regex: false
      }
    },
    fetch_method: 'ajax_vs_autocomplete'
  },
  i18n: {
    host_input_hint: '(Select host)',
    host_filter: 'Filter selection by host name:',
    service_input_hint: '(Select service)',
    service_filter: 'Filter selection by service:'
  }
}

test.skip('FormMetric renders value', () => {
  render(FormMetric, {
    props: {
      spec,
      data: 'choicea',
      backendValidation: []
    }
  })

  const element = screen.getByPlaceholderText<HTMLInputElement>('(Select metric)')

  expect(element.value).toBe('choicea')
})

test.skip('FormMetric updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'choicea',
    backendValidation: []
  })

  const element = screen.getByPlaceholderText<HTMLInputElement>('(Select metric)')
  await fireEvent.update(element, 'choiceb')

  expect(getCurrentData()).toBe('"choiceb"')
})

test.skip('FormMetric checks validators', async () => {
  render(FormMetric, {
    props: {
      spec,
      data: 'choicea',
      backendValidation: []
    }
  })

  const element = screen.getByPlaceholderText<HTMLInputElement>('(Select metric)')
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test.skip('FormMetric renders backend validation messages', async () => {
  render(FormMetric, {
    props: {
      spec,
      data: 'choicea',
      backendValidation: [
        {
          location: [],
          message: 'Backend error message',
          replacement_value: 'some_replacement_value'
        }
      ]
    }
  })

  await screen.findByText('Backend error message')
  const element = screen.getByPlaceholderText<HTMLInputElement>('(Select metric)')
  expect(element.value).toBe('some_replacement_value')
})
