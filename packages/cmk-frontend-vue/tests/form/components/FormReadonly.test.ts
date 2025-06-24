/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormReadonly from '@/form/components/FormReadonly.vue'

function getSpec(specType: 'integer' | 'float'): FormSpec.Integer | FormSpec.Float {
  return {
    type: specType,
    title: 'fooTitle',
    help: 'fooHelp',
    i18n_base: { required: 'required' },
    label: 'fooLabel',
    unit: 'fooUnit',
    validators: [],
    input_hint: 'fooInputHint'
  }
}

test('FormReadonly renders integer', () => {
  render(FormReadonly, {
    props: {
      spec: getSpec('integer'),
      data: 42,
      backendValidation: []
    }
  })
  screen.getByText('42')
})

test('FormReadonly updates integer', async () => {
  const props = {
    spec: getSpec('integer'),
    data: 42,
    backendValidation: []
  }

  const { rerender } = render(FormReadonly, {
    props
  })
  screen.getByText('42')
  await rerender({ ...props, data: 41 })
  screen.getByText('41')
})

test('FormReadonly renders float', () => {
  render(FormReadonly, {
    props: {
      spec: getSpec('float'),
      data: 42.23,
      backendValidation: []
    }
  })
  screen.getByText('42.23')
})

const stringFormSpec: FormSpec.String = {
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

test('FormReadonly renders string', () => {
  render(FormReadonly, {
    props: {
      spec: stringFormSpec,
      data: 'foo',
      backendValidation: []
    }
  })
  screen.getByText('foo')
})

const dictionaryFormSpec: FormSpec.Dictionary = {
  type: 'dictionary',
  title: 'fooTitle',
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
      required: true,
      default_value: 'baz',
      parameter_form: stringFormSpec,
      group: null
    }
  ]
}

test('FormReadonly renders dictionary', () => {
  render(FormReadonly, {
    props: {
      spec: dictionaryFormSpec,
      backendValidation: [],
      data: { bar: 'baz' }
    }
  })
  screen.getByText('baz')
})

test('FormReadonly renders dictionary with default value', () => {
  render(FormReadonly, {
    props: {
      spec: dictionaryFormSpec,
      backendValidation: [],
      data: {}
    }
  })
  screen.getByRole('table')
  expect(screen.queryByText('baz')).toBeNull()
})

const singleChoiceFormSpec: FormSpec.SingleChoice = {
  type: 'single_choice',
  title: 'fooTitle',
  input_hint: '',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  no_elements_text: 'no_text',
  elements: [
    { name: 'choice1', title: 'Choice 1' },
    { name: 'choice2', title: 'Choice 2' }
  ],
  label: 'fooLabel',
  frozen: false,
  validators: []
}

test('FormReadonly renders single_choice', () => {
  render(FormReadonly, {
    props: {
      spec: singleChoiceFormSpec,
      backendValidation: [],
      data: 'choice1'
    }
  })
  screen.getByText('Choice 1')
  expect(screen.queryByText('choice1')).toBeNull()
})

const listFormSpec: FormSpec.List = {
  type: 'list',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  element_template: stringFormSpec,
  element_default_value: '',
  editable_order: false,
  add_element_label: 'Add element',
  remove_element_label: 'Remove element',
  no_element_label: 'No element'
}

test('FormReadonly renders list', () => {
  render(FormReadonly, {
    props: {
      spec: listFormSpec,
      backendValidation: [],
      data: ['foo', 'bar']
    }
  })
  screen.getByText('foo')
  screen.getByText('bar')
})

const cascadingSingleChoiceFormSpec: FormSpec.CascadingSingleChoice = {
  type: 'cascading_single_choice',
  title: 'fooTitle',
  label: 'fooLabel',
  layout: 'horizontal',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  validators: [],
  input_hint: null,
  no_elements_text: '',
  elements: [
    {
      name: 'stringChoice',
      title: 'stringChoiceTitle',
      default_value: 'bar',
      parameter_form: stringFormSpec
    },
    {
      name: 'integerChoice',
      title: 'integerChoiceTitle',
      default_value: 5,
      parameter_form: getSpec('integer')
    }
  ]
}

test('FormReadonly renders cascading/string, 1st choice', () => {
  render(FormReadonly, {
    props: {
      spec: cascadingSingleChoiceFormSpec,
      backendValidation: [],
      data: ['stringChoice', 'baz']
    }
  })
  // Title of element choice
  screen.getByText('stringChoiceTitle:')
  // Value of element
  screen.getByText('baz')
})

test('FormReadonly renders cascading/integer, 2nd choice', () => {
  render(FormReadonly, {
    props: {
      spec: cascadingSingleChoiceFormSpec,
      backendValidation: [],
      data: ['integerChoice', 23]
    }
  })
  // Title of element choice
  screen.getByText('integerChoiceTitle:')
  // Value of element
  screen.getByText(23)
})

const booleanChoiceFormSpec: FormSpec.BooleanChoice = {
  type: 'boolean_choice',
  title: 'fooTitle',
  label: 'fooLabel',
  help: 'fooHelp',
  text_on: 'on',
  text_off: 'off',
  validators: []
}

test('FormReadonly renders boolean: on', () => {
  render(FormReadonly, {
    props: {
      spec: booleanChoiceFormSpec,
      backendValidation: [],
      data: true
    }
  })
  // Title of cascading
  screen.getByText('fooLabel: on')
})

test('FormReadonly renders boolean: off', () => {
  render(FormReadonly, {
    props: {
      spec: booleanChoiceFormSpec,
      backendValidation: [],
      data: false
    }
  })
  // Title of cascading
  screen.getByText('fooLabel: off')
})

test('FormReadonly renders time_span: simple', () => {
  render(FormReadonly, {
    props: {
      spec: {
        type: 'time_span',
        displayed_magnitudes: ['millisecond', 'second', 'minute'],
        i18n: { minute: 'ut_minute', second: 'ut_second', millisecond: 'ut_ms' }
      } as FormSpec.TimeSpan,
      backendValidation: [],
      data: 66.6
    }
  })
  screen.getByText('1 ut_minute 6 ut_second 600 ut_ms')
})

const multilineTextFormSpec: FormSpec.MultilineText = {
  type: 'multiline_text',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  label: 'fooLabel',
  macro_support: false,
  monospaced: false,
  input_hint: null
}
test('FormReadonly renders multiline_text', () => {
  render(FormReadonly, {
    props: {
      spec: multilineTextFormSpec,
      backendValidation: [],
      data: 'BLABLA'
    }
  })
  // Title of cascading
  screen.getByText('BLABLA')
})

const labelsFormSpec: FormSpec.Labels = {
  type: 'labels',
  title: 'fooTitle',
  help: 'fooHelp',
  i18n: {
    remove_label: 'i18n remove_label',
    add_some_labels: 'Add some labels',
    key_value_format_error: 'Key value format error',
    max_labels_reached: 'Max labels reached',
    uniqueness_error: 'Uniqueness error'
  },
  max_labels: 3,
  autocompleter: {
    data: { ident: '', params: {} },
    fetch_method: 'ajax_vs_autocomplete'
  } as FormSpec.Autocompleter,
  label_source: 'discovered',
  validators: []
}

test('FormReadonly renders labels', () => {
  render(FormReadonly, {
    props: {
      spec: labelsFormSpec,
      backendValidation: [],
      data: { key1: 'value1', key2: 'value2' }
    }
  })
  screen.getByText('key1: value1')
  screen.getByText('key2: value2')
  expect(screen.queryByText('key3: value3')).toBeNull()
})

const dualListChoiceFormSpec: FormSpec.DualListChoice = {
  type: 'dual_list_choice',
  title: 'fooTitle',
  help: 'fooHelp',
  show_toggle_all: true,
  i18n: {
    add: 'add',
    remove: 'remove',
    add_all: 'add_all',
    remove_all: 'remove_all',
    available_options: 'available_options',
    selected_options: 'selected_options',
    selected: 'selected',
    no_elements_available: 'no_elements_available',
    no_elements_selected: 'no_elements_selected',
    autocompleter_loading: 'autocompleter_loading',
    search_available_options: 'search_available_options',
    search_selected_options: 'search_selected_options',
    and_x_more: 'and_x_more'
  },
  validators: [],
  elements: [
    { name: 'choice1', title: 'Choice 1' },
    { name: 'choice2', title: 'Choice 2' },
    { name: 'choice3', title: 'Choice 3' }
  ]
}

test('FormReadonly renders dual list choice', () => {
  render(FormReadonly, {
    props: {
      spec: dualListChoiceFormSpec,
      backendValidation: [],
      data: [
        { name: 'choice1', title: 'Choice 1' },
        { name: 'choice2', title: 'Choice 2' }
      ]
    }
  })
  screen.getByText('Choice 1')
  screen.getByText('Choice 2')
  expect(screen.queryByText('Choice 3')).toBeNull()
})
