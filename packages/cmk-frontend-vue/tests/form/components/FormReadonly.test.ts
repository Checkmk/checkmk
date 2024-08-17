import { render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import FormReadonly from '@/form/components/FormReadonly.vue'

function getSpec(specType: 'integer' | 'float'): FormSpec.Integer | FormSpec.Float {
  return {
    type: specType,
    title: 'fooTitle',
    help: 'fooHelp',
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
  validators: [],
  input_hint: ''
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
  validators: [],
  groups: [],
  elements: [
    {
      ident: 'bar',
      required: true,
      default_value: 'baz',
      parameter_form: stringFormSpec
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
  help: 'fooHelp',
  validators: [],
  input_hint: '',
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
  // Title of cascading
  screen.getByText('fooTitle')
  // Title of element choice
  screen.getByText('stringChoiceTitle')
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
  // Title of cascading
  screen.getByText('fooTitle')
  // Title of element choice
  screen.getByText('integerChoiceTitle')
  // Value of element
  screen.getByText(23)
})

const booleanChoiceFormSpec: FormSpec.BooleanChoice = {
  type: 'boolean_choice',
  title: 'fooTitle',
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
  screen.getByText('on')
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
  screen.getByText('off')
})

const multilineTextFormSpec: FormSpec.MultilineText = {
  type: 'multiline_text',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: []
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
