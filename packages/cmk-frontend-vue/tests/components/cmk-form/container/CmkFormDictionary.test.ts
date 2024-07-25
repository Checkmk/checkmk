import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormDictionary from '@/components/cmk-form/container/CmkFormDictionary.vue'
import * as FormSpec from '@/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

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
    data: {},
    backendValidation: []
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox', { name: 'barTitle' })
  expect(checkbox.checked).toBeFalsy()

  expect(getCurrentData()).toMatchObject({})
})

test('CmkFormDictionary displays dictelement data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: { bar: 'some_value' },
    backendValidation: []
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
      data: {},
      backendValidation: []
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
      data: {},
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  const element = screen.getByRole('textbox', { name: 'barTitle' })
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('CmkFormDictionary render backend validation message', async () => {
  render(CmkFormDictionary, {
    props: {
      spec,
      data: { bar: 'some_value' },
      backendValidation: [
        { location: ['bar'], message: 'Backend error message', invalid_value: 'other_value' }
      ]
    }
  })

  await screen.findByDisplayValue('other_value')

  screen.getByText('Backend error message')
})

test('CmkFormDictionary enable element, render backend validation message', async () => {
  render(CmkFormDictionary, {
    props: {
      spec,
      data: {},
      backendValidation: [
        { location: ['bar'], message: 'Backend error message', invalid_value: '' }
      ]
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  await screen.findByText('Backend error message')
})

test('CmkFormDictionary appends default of required element if missing in data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: {
      type: 'dictionary',
      title: 'fooTitle',
      help: 'fooHelp',
      validators: [],
      elements: [
        {
          ident: 'bar',
          required: true,
          default_value: 'baz',
          parameter_form: stringFormSpec
        }
      ]
    } as FormSpec.Dictionary,
    data: {},
    backendValidation: []
  })

  await screen.findByDisplayValue('baz')

  expect(getCurrentData()).toBe('{"bar":"baz"}')
})
