import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormDictionary from '@/components/cmk-form/container/CmkFormDictionary.vue'
import * as FormSpec from '@/vue_formspec_components'
import { type ValidationMessages } from '@/utils'
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
  title: 'barTitle',
  help: 'barHelp',
  validators: stringValidators,
  input_hint: ''
}

const spec: FormSpec.Dictionary = {
  type: 'dictionary',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  elements: [
    {
      ident: 'bar',
      required: false,
      default_value: 'baz',
      parameter_form: stringFormSpec
    }
  ]
}

test('CmkFormDictionary empty on non-required elements results in empty form data', () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: {}
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox', { name: 'barTitle' })
  expect(checkbox.checked).toBeFalsy()

  expect(getCurrentData()).toMatchObject({})
})

test('CmkFormDictionary displays dictelement data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: { bar: 'some_value' }
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox', { name: 'barTitle' })
  expect(checkbox.checked).toBeTruthy()

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'barTitle' })
  expect(element.value).toBe('some_value')

  expect(getCurrentData()).toBe('{"bar":"some_value"}')
})

test('CmkFormDictionary checking non-required element fills default', async () => {
  render(CmkFormDictionary, {
    props: {
      spec,
      data: {}
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'barTitle' })
  expect(element.value).toBe('baz')
})

test('CmkFormDictionary enable element, check frontend validators', async () => {
  render(CmkFormDictionary, {
    props: {
      spec,
      data: {}
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  const element = screen.getByRole('textbox', { name: 'barTitle' })
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('CmkFormDictionary enable element, render backend validation message', async () => {
  const wrapper = mount(CmkFormDictionary, {
    props: {
      spec,
      data: {}
    }
  })
  const checkbox = wrapper.get('input[type="checkbox"]')
  await checkbox.trigger('click')

  const validation_messages = [
    { location: ['bar'], message: 'Backend error message', invalid_value: '' }
  ] as ValidationMessages
  wrapper.vm.setValidation(validation_messages)
  await wrapper.vm.$nextTick()
  expect(wrapper.get('li').text()).toBe('Backend error message')
})
