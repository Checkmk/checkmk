import { fireEvent, render, screen } from '@testing-library/vue'
import FormSingleChoice from '@/components/cmk-form/forms/FormSingleChoice.vue'
import type * as FormSpec from '@/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

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

test('FormSingleChoice renders value', () => {
  render(FormSingleChoice, {
    props: {
      spec,
      data: 'choice1',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })

  expect(element.value).toBe('choice1')
})

test('FormSingleChoice updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'choice1',
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('combobox', { name: 'fooLabel' })
  await fireEvent.update(element, 'choice2')

  expect(getCurrentData()).toBe('"choice2"')
})

test('FormSingleChoice renders backend validation messages', async () => {
  render(FormSingleChoice, {
    props: {
      spec,
      data: 'choice1',
      backendValidation: [
        {
          location: [],
          message: 'Backend error message',
          invalid_value: ''
        }
      ]
    }
  })

  await screen.findByText('Backend error message')
})
