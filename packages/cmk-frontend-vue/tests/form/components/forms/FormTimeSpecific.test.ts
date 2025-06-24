/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import FormEdit from '@/form/components/FormEdit.vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const embeddedSpec: FormSpec.String = {
  type: 'string',
  title: 'barTitle',
  help: 'barHelp',
  label: null,
  i18n_base: { required: 'required' },
  validators: [],
  input_hint: '',
  autocompleter: null,
  field_size: 'SMALL'
}

const listSpec: FormSpec.List = {
  type: 'list',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  element_template: embeddedSpec,
  element_default_value: 'listDefault',
  add_element_label: 'Add',
  remove_element_label: 'Remove',
  no_element_label: 'no_text',
  editable_order: true
}

const enabledSpec: FormSpec.Dictionary = {
  type: 'dictionary',
  title: 'fooTitle',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  validators: [],
  groups: [],
  additional_static_elements: null,
  no_elements_text: 'no_text',
  elements: [
    {
      name: 'tp_default_value',
      render_only: false,
      required: true,
      default_value: 'foo',
      parameter_form: embeddedSpec,
      group: null
    },
    {
      name: 'tp_values',
      render_only: false,
      required: true,
      default_value: [],
      parameter_form: listSpec,
      group: null
    }
  ]
}

const spec: FormSpec.TimeSpecific = {
  type: 'time_specific',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  time_specific_values_key: 'tp_values',
  default_value_key: 'tp_default_value',
  i18n: {
    enable: 'enable',
    disable: 'disable'
  },
  parameter_form_disabled: embeddedSpec,
  parameter_form_enabled: enabledSpec
}

test('FormTimeSpecific test toggle button text', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: '42',
      backendValidation: []
    }
  })

  const toggleButton = screen.getByText<HTMLButtonElement>('enable')
  await fireEvent.click(toggleButton)
  expect(toggleButton.textContent).toBe('disable')
  await fireEvent.click(toggleButton)
  expect(toggleButton.textContent).toBe('enable')
})

test('FormTimeSpecific test enable/disable', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: '42',
    backendValidation: []
  })

  const toggleButton = screen.getByText<HTMLButtonElement>('enable')
  await fireEvent.click(toggleButton)
  expect(getCurrentData()).toBe('{"tp_default_value":"42","tp_values":[]}')

  await fireEvent.click(toggleButton)
  expect(getCurrentData()).toBe('"42"')
})

test('FormTimeSpecific: check embedded validation message', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: { tp_default_value: '42', tp_values: [] },
      backendValidation: [
        {
          location: ['tp_default_value'],
          message: 'Backend error message',
          replacement_value: 'other_value'
        }
      ]
    }
  })
  // Search updated value in embeddedSpec
  await screen.findByDisplayValue('other_value')
})

test('FormTimeSpecific: check time specific validation message', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: '42',
      backendValidation: [
        {
          location: [],
          message: 'TimeSpecific problems',
          replacement_value: '42'
        }
      ]
    }
  })
  // Search error message on screen
  await screen.findByText('TimeSpecific problems')
})
