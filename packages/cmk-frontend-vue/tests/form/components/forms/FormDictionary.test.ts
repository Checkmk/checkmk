/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, waitFor, render, screen } from '@testing-library/vue'
import FormDictionary from '@/form/components/forms/FormDictionary/FormDictionary.vue'
import FormEdit from '@/form/components/FormEdit.vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const stringValidators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const stringFormSpec: FormSpec.String = {
  type: 'string',
  title: 'barTitle',
  help: 'barHelp',
  label: 'barLabel',
  i18n_base: { required: 'required' },
  validators: stringValidators,
  input_hint: '',
  autocompleter: null,
  field_size: 'SMALL'
}

const dictElementGroupFormSpec: FormSpec.DictionaryGroup = {
  key: 'titlehelp',
  title: 'title',
  help: 'help',
  layout: 'horizontal'
}

const spec: FormSpec.Dictionary = {
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
      name: 'bar',
      render_only: false,
      required: false,
      default_value: 'barDefaultValue',
      parameter_form: stringFormSpec,
      group: dictElementGroupFormSpec
    }
  ]
}

test('FormDictionary empty on non-required elements results in empty form data', () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: {},
    backendValidation: []
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox', { name: 'barTitle' })
  expect(checkbox.checked).toBeFalsy()

  expect(getCurrentData()).toMatchObject({})
})

test('FormDictionary displays dictelement data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: { bar: 'some_value' },
    backendValidation: []
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox', { name: 'barTitle' })
  await waitFor(() => expect(checkbox.getAttribute('aria-checked')).toBe('true'))

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'barLabel' })
  expect(element.value).toBe('some_value')

  expect(getCurrentData()).toBe('{"bar":"some_value"}')
})

test('FormDictionary checking non-required element fills default', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: {},
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'barLabel' })
  expect(element.value).toBe('barDefaultValue')
})

test('FormDictionary enable element, check frontend validators', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: {},
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  const element = screen.getByRole('textbox', { name: 'barLabel' })
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormDictionary render backend validation message of children', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: { bar: 'some_value' },
      backendValidation: [
        { location: ['bar'], message: 'Backend error message', replacement_value: 'other_value' }
      ]
    }
  })

  await screen.findByDisplayValue('other_value')

  screen.getByText('Backend error message')
})

test('FormDictionary renders its own backend validation message', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: { bar: 'some_value' },
      backendValidation: [
        { location: [], message: 'Backend error message', replacement_value: null }
      ]
    }
  })

  screen.getByText('Backend error message')
})

test('FormDictionary renders required only once depending on label presence', async () => {
  const optionalString: FormSpec.String = {
    type: 'string',
    title: 'optionalTitle',
    help: 'optionalHelp',
    label: 'optionalLabel',
    i18n_base: { required: 'required' },
    validators: stringValidators,
    input_hint: '',
    autocompleter: null,
    field_size: 'SMALL'
  }

  const optionalUnlabeledString: FormSpec.String = {
    type: 'string',
    title: 'optionalUnlabeledTitle',
    help: 'optionalUnlabeledHelp',
    label: null,
    i18n_base: { required: 'required' },
    validators: stringValidators,
    input_hint: '',
    autocompleter: null,
    field_size: 'SMALL'
  }

  const requiredString: FormSpec.String = {
    type: 'string',
    title: 'reqLabeledTitle',
    help: 'reqLabeledHelp',
    label: 'reqLabeledLabel',
    i18n_base: { required: 'required' },
    validators: stringValidators,
    input_hint: '',
    autocompleter: null,
    field_size: 'SMALL'
  }

  const requiredUnlabeledString: FormSpec.String = {
    type: 'string',
    title: 'reqTitle',
    help: 'reqHelp',
    label: null,
    i18n_base: { required: 'required' },
    validators: stringValidators,
    input_hint: '',
    autocompleter: null,
    field_size: 'SMALL'
  }

  const localSpec: FormSpec.Dictionary = {
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
        name: 'bar',
        render_only: false,
        required: true,
        default_value: '',
        parameter_form: requiredUnlabeledString,
        group: dictElementGroupFormSpec
      },
      {
        name: 'labeledBar',
        render_only: false,
        required: true,
        default_value: '',
        parameter_form: requiredString,
        group: dictElementGroupFormSpec
      },
      {
        name: 'optional',
        render_only: false,
        required: false,
        default_value: '',
        parameter_form: optionalUnlabeledString,
        group: dictElementGroupFormSpec
      },
      {
        name: 'labeledOptional',
        render_only: false,
        required: false,
        default_value: '',
        parameter_form: optionalString,
        group: dictElementGroupFormSpec
      }
    ]
  }

  render(FormEdit, {
    props: {
      spec: localSpec,
      data: { optional: 'some_value', labeledOptional: 'other_value' },
      backendValidation: []
    }
  })

  expect(screen.getAllByText('(required)')).toHaveLength(3)
})

test.skip('FormDictionary enable element, render backend validation message', async () => {
  render(FormDictionary, {
    props: {
      spec,
      data: {},
      backendValidation: [
        { location: ['bar'], message: 'Backend error message', replacement_value: '' }
      ]
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  await screen.findByText('Backend error message')
})

test('FormDictionary appends default of required element if missing in data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: {
      type: 'dictionary',
      title: 'fooTitle',
      help: 'fooHelp',
      i18n_base: { required: 'required' },
      groups: [],
      validators: [],
      no_elements_text: 'no_text',
      additional_static_elements: null,
      elements: [
        {
          name: 'bar',
          render_only: false,
          required: true,
          default_value: 'baz',
          parameter_form: stringFormSpec,
          group: dictElementGroupFormSpec
        }
      ]
    } as FormSpec.Dictionary,
    data: {},
    backendValidation: []
  })

  await screen.findByDisplayValue('baz')

  expect(getCurrentData()).toBe('{"bar":"baz"}')
})

test('FormDictionary checks frontend validators on existing element', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: { bar: 'some_value' },
      backendValidation: []
    }
  })

  const element = screen.getByRole('textbox', { name: 'barLabel' })
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormDictionary reads new defaultValue on updated spec', async () => {
  function getSpec(name: string): FormSpec.Dictionary {
    return {
      type: 'dictionary',
      title: 'fooTitle',
      help: 'fooHelp',
      i18n_base: { required: 'required' },
      groups: [],
      validators: [],
      additional_static_elements: null,
      no_elements_text: 'no_text',
      elements: [
        {
          name: name,
          render_only: false,
          required: true,
          default_value: 'something',
          parameter_form: stringFormSpec,
          group: null
        }
      ]
    }
  }

  const { getCurrentData, rerender } = renderFormWithData({
    spec: getSpec('some_id'),
    data: {},
    backendValidation: []
  })

  await rerender({ spec: getSpec('some_other_id'), data: {}, backendValidation: [] })

  expect(getCurrentData()).toBe('{"some_other_id":"something"}')
})

test('FormDictionary is able to be rerenderd: static value', async () => {
  // before this test was written, some data handling logic was in onBeforeMount
  // which is only executed once. os if the spec is changed, it was not executed again.

  function getSpec(staticElements: Record<string, unknown>): FormSpec.Dictionary {
    return {
      type: 'dictionary',
      title: 'fooTitle',
      help: 'fooHelp',
      i18n_base: { required: 'required' },
      additional_static_elements: staticElements,
      no_elements_text: 'no_text',
      groups: [],
      validators: [],
      elements: []
    }
  }

  const { getCurrentData, rerender } = renderFormWithData({
    spec: getSpec({ some_key: 'some_value' }),
    data: {},
    backendValidation: []
  })

  // wait until component is renderd and expected data is shown
  await screen.findByText('{"some_key":"some_value"}')

  await rerender({
    spec: getSpec({ another_key: 'another_value' }),
    data: {},
    backendValidation: []
  })

  expect(getCurrentData()).toBe('{"another_key":"another_value"}')
})

test('Default values of dict elements dont influence each other', async () => {
  const innerList: FormSpec.List = {
    type: 'list',
    title: 'innerList',
    help: '',
    validators: [],
    element_template: stringFormSpec,
    element_default_value: 'default value',
    editable_order: false,
    add_element_label: 'Add inner element',
    remove_element_label: 'Remove inner element',
    no_element_label: 'No element'
  }

  const dictSpec: FormSpec.Dictionary = {
    type: 'dictionary',
    title: 'dictTitle',
    help: 'fooHelp',
    i18n_base: { required: 'required' },
    validators: [],
    groups: [],
    no_elements_text: 'no_text',
    additional_static_elements: null,
    elements: [
      {
        name: 'bar',
        render_only: false,
        required: false,
        default_value: [],
        parameter_form: innerList,
        group: dictElementGroupFormSpec
      }
    ]
  }

  const outerList: FormSpec.List = {
    type: 'list',
    title: 'outerList',
    help: '',
    validators: [],
    element_template: dictSpec,
    element_default_value: {},
    editable_order: false,
    add_element_label: 'Add outer element',
    remove_element_label: 'Remove outer element',
    no_element_label: 'No element'
  }

  const { getCurrentData } = renderFormWithData({
    spec: outerList,
    data: [],
    backendValidation: []
  })

  await fireEvent.click(screen.getByText('Add outer element'))
  await fireEvent.click(screen.getByRole('checkbox'))
  await fireEvent.click(screen.getByText('Add inner element'))

  const textbox = screen.getByRole('textbox')
  await fireEvent.update(textbox, 'some value')

  await fireEvent.click(screen.getByText('Add outer element'))
  await fireEvent.click(screen.getAllByRole('checkbox')[1]!)
  await fireEvent.click(screen.getAllByText('Add inner element')[1]!)

  expect(getCurrentData()).toBe('[{"bar":["some value"]},{"bar":["default value"]}]')
})
