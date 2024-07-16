import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormString from '@/components/cmk-form/element/CmkFormString.vue'
import * as FormSpec from '@/vue_formspec_components'
import { type ValidationMessages } from '@/utils'
import { renderFormWithData } from '../cmk-form-helper'
import { mount } from '@vue/test-utils'

const validators: FormSpec.Validators[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const spec: FormSpec.String = {
  type: 'string',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  input_hint: 'fooInputHint'
}

test('CmkFormString renders value', () => {
  render(CmkFormString, {
    props: {
      spec,
      data: 'fooData'
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooTitle' })

  expect(element.value).toBe('fooData')
})

test('CmkFormString updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'fooData'
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooTitle' })
  await fireEvent.update(element, 'some_other_value')

  expect(getCurrentData()).toBe('"some_other_value"')
})

test('CmkFormString checks validators', async () => {
  render(CmkFormString, {
    props: {
      spec,
      data: 'fooData'
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooTitle' })
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('CmkFormString renders backend validation messages', async () => {
  const wrapper = mount(CmkFormString, {
    props: {
      spec,
      data: 'fooData'
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
