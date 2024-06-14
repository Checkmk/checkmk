import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormFloat from '@/components/cmk-form/element/CmkFormFloat.vue'
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

const spec: FormSpec.Float = {
  type: 'float',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  label: 'fooLabel',
  unit: 'fooUnit'
}

test('CmkFormFloat renders value', () => {
  render(CmkFormFloat, {
    props: {
      spec,
      validation: [],
      data: 42.5
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })

  expect(element.value).toBe('42.5')
})

test('CmkFormFloat updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    validation: [],
    data: 42.5
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  await fireEvent.update(element, '23.1')

  expect(getCurrentData()).toBe('23.1')
})

test('CmkFormFloat checks validators', async () => {
  render(CmkFormFloat, {
    props: {
      spec,
      validation: [],
      data: 42.5
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox', { name: 'fooLabel' })
  await fireEvent.update(element, '0.1')

  screen.getByText('Value must be between 1 and 100')
})

test('CmkFormFloat renders backend validation messages', () => {
  render(CmkFormFloat, {
    props: {
      spec,
      validation: [{ location: [], message: 'Backend error message' }] as ValidationMessages,
      data: 42.0
    }
  })

  screen.getByText('Backend error message')
})
