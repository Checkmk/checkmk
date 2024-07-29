import { fireEvent, render, screen } from '@testing-library/vue'
import CmkFormList from '@/components/cmk-form/container/CmkFormList.vue'
import type * as FormSpec from '@/vue_formspec_components'

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

const spec: FormSpec.List = {
  type: 'list',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  element_template: stringFormSpec,
  element_default_value: '',
  editable_order: false,
  add_element_label: 'Add element',
  remove_element_label: 'Remove element',
  no_element_label: 'No element'
}

test('CmkFormList renders backend validation messages', async () => {
  render(CmkFormList, {
    props: {
      spec,
      data: [],
      backendValidation: [{ location: [], message: 'Backend error message', invalid_value: '' }]
    }
  })

  screen.getByText('Backend error message')
})

test('CmkFormList updated backend child validation shows validation error', async () => {
  const { rerender } = render(CmkFormList, {
    props: {
      spec,
      data: ['some value'],
      backendValidation: []
    }
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['some value'],
    backendValidation: [
      { location: ['0'], message: 'Backend error message', invalid_value: 'other value' }
    ]
  })

  screen.getByText('Backend error message')
  const textbox = screen.getByRole<HTMLInputElement>('textbox', { name: 'barTitle' })
  expect(textbox.value).toBe('other value')
})

test('CmkFormList local child validation overwrites backend validation', async () => {
  render(CmkFormList, {
    props: {
      spec,
      data: ['some value'],
      backendValidation: [
        { location: ['0'], message: 'Backend error message', invalid_value: 'other value' }
      ]
    }
  })

  const textbox = await screen.findByRole<HTMLInputElement>('textbox', { name: 'barTitle' })
  await fireEvent.update(textbox, '')

  screen.getByText('String length must be between 1 and 20')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('CmkFormList shows frontend validation on existing element', async () => {
  render(CmkFormList, {
    props: {
      spec,
      data: ['some_value'],
      backendValidation: []
    }
  })

  const textbox = await screen.findByRole<HTMLInputElement>('textbox', { name: 'barTitle' })
  await fireEvent.update(textbox, '')

  screen.getByText('String length must be between 1 and 20')
})
