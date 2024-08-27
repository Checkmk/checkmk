import { fireEvent, render, screen } from '@testing-library/vue'
import FormDictionary from '@/form/components/forms/FormDictionary.vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const stringValidators: FormSpec.Validator[] = [
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
  layout: 'default',
  validators: [],
  groups: [],
  elements: [
    {
      ident: 'bar',
      required: false,
      default_value: 'baz',
      parameter_form: stringFormSpec
    }
  ]
}

test('FormDictionary empty on non-required elements results in empty form data', () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: {},
    backendValidation: []
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox', { name: 'barTitle' })
  expect(checkbox.checked).toBeFalsy()

  expect(getCurrentData()).toMatchObject({})
})

test('FormDictionary displays dictelement data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: { bar: 'some_value' },
    backendValidation: []
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox', { name: 'barTitle' })
  expect(checkbox.checked).toBeTruthy()

  const element = screen.getByRole<HTMLInputElement>('textbox')
  expect(element.value).toBe('some_value')

  expect(getCurrentData()).toBe('{"bar":"some_value"}')
})

test('FormDictionary checking non-required element fills default', async () => {
  render(FormDictionary, {
    props: {
      spec,
      data: {},
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  const element = screen.getByRole<HTMLInputElement>('textbox')
  expect(element.value).toBe('baz')
})

test('FormDictionary enable element, check frontend validators', async () => {
  render(FormDictionary, {
    props: {
      spec,
      data: {},
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole('checkbox', { name: 'barTitle' })
  await fireEvent.click(checkbox)

  const element = screen.getByRole('textbox')
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})

test('FormDictionary render backend validation message', async () => {
  render(FormDictionary, {
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

test.skip('FormDictionary enable element, render backend validation message', async () => {
  render(FormDictionary, {
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

test('FormDictionary appends default of required element if missing in data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: {
      type: 'dictionary',
      title: 'fooTitle',
      layout: 'default',
      help: 'fooHelp',
      groups: [],
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

test('FormDictionary checks frontend validators on existing element', async () => {
  render(FormDictionary, {
    props: {
      spec,
      data: { bar: 'some_value' },
      backendValidation: []
    }
  })

  const element = await screen.getByRole('textbox')
  await fireEvent.update(element, '')

  screen.getByText('String length must be between 1 and 20')
})
