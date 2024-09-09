import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import FormSimplePassword from '@/form/components/forms/FormSimplePassword.vue'

const validators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    error_message: 'Min length must be 1'
  }
]
const spec: FormSpec.SimplePassword = {
  type: 'simple_password',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators
}

test('FormSimplePassword renders validation message', async () => {
  render(FormSimplePassword, {
    props: {
      spec,
      data: ['encrypted_pw', false],
      backendValidation: [{ location: [], message: 'Invalid password', invalid_value: '' }]
    }
  })

  await screen.findByText('Invalid password')
})

test('FormSimplePassword user input', async () => {
  render(FormSimplePassword, {
    props: {
      spec,
      data: ['encrypted_pw', true],
      backendValidation: []
    }
  })
  const element = screen.getByLabelText<HTMLInputElement>('')
  await fireEvent.update(element, '')
  screen.getByText('Min length must be 1')
  await fireEvent.update(element, '23')
  expect(screen.queryByText('Min length must be 1')).toBeNull()
})

test('FormSimplePassword updates validation', async () => {
  const { rerender } = render(FormSimplePassword, {
    props: {
      spec,
      data: ['encrypted_pw', true],
      backendValidation: []
    }
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['encrypted_pw', true],
    backendValidation: [
      {
        location: [],
        message: 'Backend error message',
        invalid_value: ''
      }
    ]
  })

  screen.getByText('Backend error message')
  const element = screen.getByLabelText<HTMLInputElement>('')
  expect(element.value).toBe('')
})
