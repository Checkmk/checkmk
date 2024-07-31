import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'
import CmkFormMultilineText from '@/components/cmk-form/element/CmkFormMultilineText.vue'

const validators: FormSpec.Validators[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const spec: FormSpec.MultilineText = {
  type: 'multiline_text',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  input_hint: 'fooInputHint'
}

test('CmkFormMultilineText renders value', () => {
  render(CmkFormMultilineText, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLTextAreaElement>('textbox')

  expect(element.value).toBe('fooData')
})

test('CmkFormMultilineText updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'fooData',
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(element, 'some_other_value')

  expect(getCurrentData()).toBe('"some_other_value"')
})

test('CmkFormMultilineText checks validators', async () => {
  render(CmkFormMultilineText, {
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

test('CmkFormMultilineText renders backend validation messages', async () => {
  render(CmkFormMultilineText, {
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
