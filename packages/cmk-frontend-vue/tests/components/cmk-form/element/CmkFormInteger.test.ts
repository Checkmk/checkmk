import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormInteger from '@/components/cmk-form/element/CmkFormInteger.vue'
import * as FormSpec from '@/vue_formspec_components'
import { type ValidationMessages } from '@/utils'
import { renderFormWithData } from '../cmk-form-helper'

const validators: FormSpec.Validators[] = [
  {
    type: 'number_in_range',
    min_value: 1,
    max_value: 100,
    error_message: 'Value must be between 1 and 100'
  }
]

const spec: FormSpec.Integer = {
  type: 'integer',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  label: 'fooLabel',
  unit: 'fooUnit'
}

test('CmkFormInteger renders value', () => {
  render(CmkFormInteger, {
    props: {
      spec,
      validation: [],
      data: 42
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })

  expect(element.value).toBe('42')
})

test('CmkFormInteger updates data', async () => {
  const { getCurrentData: currentData } = renderFormWithData({
    spec,
    validation: [],
    data: 42
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  await fireEvent.update(element, '23')

  expect(currentData()).toBe('23')
})

test('CmkFormInteger checks validators', async () => {
  render(CmkFormInteger, {
    props: {
      spec,
      validation: [],
      data: 42
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  await fireEvent.update(element, '0')

  screen.getByText('Value must be between 1 and 100')
})

test('CmkFormInteger renders backend validation messages', () => {
  render(CmkFormInteger, {
    props: {
      spec,
      validation: [{ location: [], message: 'Backend error message' }] as ValidationMessages,
      data: 42
    }
  })

  screen.getByText('Backend error message')
})
