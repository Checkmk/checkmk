import { fireEvent, render, screen } from '@testing-library/vue'
import FormString from '@/components/cmk-form/forms/FormString.vue'
import type * as FormSpec from '@/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const validators: FormSpec.Validator[] = [
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

test('FormString renders value', () => {
  render(FormString, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')

  expect(element.value).toBe('fooData')
})

test('FormString updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'fooData',
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(element, 'some_other_value')

  expect(getCurrentData()).toBe('"some_other_value"')
})

test('FormString checks validators', async () => {
  render(FormString, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormString renders backend validation messages', async () => {
  render(FormString, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: [
        {
          location: [],
          message: 'Backend error message',
          invalid_value: 'some_invalid_value'
        }
      ]
    }
  })

  await screen.findByText('Backend error message')
  const element = screen.getByRole<HTMLInputElement>('textbox')
  expect(element.value).toBe('some_invalid_value')
})
