import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormSingleChoice from '@/components/cmk-form/element/CmkFormSingleChoice.vue'
import * as FormSpec from '@/vue_formspec_components'
import { type ValidationMessages } from '@/utils'
import { renderFormWithData } from '../cmk-form-helper'
import { mount } from '@vue/test-utils'

const spec: FormSpec.SingleChoice = {
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

test('CmkFormSingleChoice renders value', () => {
  render(CmkFormSingleChoice, {
    props: {
      spec,
      data: 'choice1'
    }
  })

  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })

  expect(element.value).toBe('choice1')
})

test('CmkFormSingleChoice updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'choice1'
  })

  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })
  await fireEvent.update(element, 'choice2')

  expect(getCurrentData()).toBe('"choice2"')
})

test('CmkFormSingleChoice renders backend validation messages', async () => {
  const wrapper = mount(CmkFormSingleChoice, {
    props: {
      spec,
      data: 'choice1'
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
