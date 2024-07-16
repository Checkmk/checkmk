import { fireEvent, render, screen } from '@testing-library/vue'
import * as FormSpec from '@/vue_formspec_components'
import CmkFormCascadingSingleChoice from '@/components/cmk-form/container/CmkFormCascadingSingleChoice.vue'
import type { ValidationMessages } from '@/utils'
import { renderFormWithData } from '../cmk-form-helper'
import { mount } from '@vue/test-utils'

const stringValidators: FormSpec.Validators[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const stringFormSpec: FormSpec.String = {
  type: 'string',
  title: 'nestedStringTitle',
  help: 'nestedStringHelp',
  validators: stringValidators,
  input_hint: ''
}

const integerFormSpec: FormSpec.Integer = {
  type: 'integer',
  title: 'nestedIntegerTitle',
  label: 'nestedIntegerLabel',
  help: 'nestedIntegerHelp',
  validators: [],
  input_hint: ''
}

const spec: FormSpec.CascadingSingleChoice = {
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
      parameter_form: integerFormSpec
    }
  ]
}

test('CmkFormCascadingSingleChoice displays data', () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'some_value']
  })

  const selectElement = screen.getByRole<HTMLInputElement>('combobox', { name: /fooLabel/i })
  expect(selectElement.value).toBe('stringChoice')

  const stringElement = screen.getByRole<HTMLInputElement>('textbox', {
    name: 'nestedStringTitle'
  })
  expect(stringElement.value).toBe('some_value')

  expect(getCurrentData()).toMatch('["stringChoice","some_value"]')
})

test('CmkFormDictionary updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'some_value']
  })

  const stringElement = screen.getByRole<HTMLInputElement>('textbox', {
    name: 'nestedStringTitle'
  })
  await fireEvent.update(stringElement, 'other_value')

  expect(getCurrentData()).toMatch('["stringChoice","other_value"]')
})

test('CmkFormCascadingSingleChoice sets default on switch', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: ['stringChoice', 'some_value']
  })

  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })
  await fireEvent.update(element, 'integerChoice')

  const integerElement = screen.getByRole<HTMLInputElement>('textbox', {
    name: 'nestedIntegerLabel'
  })
  expect(integerElement.value).toBe('5')

  expect(getCurrentData()).toMatch('["integerChoice",5]')
})

test('CmkFormCascadingSingleChoice checks validators', async () => {
  render(CmkFormCascadingSingleChoice, {
    props: {
      spec,
      data: ['stringChoice', 'some_value']
    }
  })

  const stringElement = screen.getByRole<HTMLInputElement>('textbox', {
    name: 'nestedStringTitle'
  })
  await fireEvent.update(stringElement, '')

  screen.getByText('String length must be between 1 and 20')
})

test('CmkFormCascadingSingleChoice renders backend validation messages', async () => {
  const wrapper = mount(CmkFormCascadingSingleChoice, {
    props: {
      spec,
      data: ['stringChoice', 'some_value']
    }
  })

  const validation_messages = [
    {
      location: [],
      message: 'Backend error message',
      invalid_value: ''
    }
  ] as ValidationMessages
  wrapper.vm.setValidation(validation_messages)
  await wrapper.vm.$nextTick()
  expect(wrapper.get('li').text()).toBe('Backend error message')
})
