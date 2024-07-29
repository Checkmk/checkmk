import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormString from '@/components/cmk-form/element/CmkFormString.vue'
import type * as FormSpec from '@/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

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
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooTitle' })

  expect(element.value).toBe('fooData')
})

test('CmkFormString updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'fooData',
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooTitle' })
  await fireEvent.update(element, 'some_other_value')

  expect(getCurrentData()).toBe('"some_other_value"')
})

test('CmkFormString checks validators', async () => {
  render(CmkFormString, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooTitle' })
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('CmkFormString renders backend validation messages', async () => {
  render(CmkFormString, {
    props: {
      spec,
      data: 'fooData',
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
