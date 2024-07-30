import { render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/vue_formspec_components'
import CmkFormBooleanChoice from '@/components/cmk-form/element/CmkFormBooleanChoice.vue'

function getBooleanChoice(withLabel = false): FormSpec.BooleanChoice {
  return {
    type: 'boolean_choice',
    title: 'fooTitle',
    help: 'fooHelp',
    validators: [],
    label: withLabel ? 'fooLabel' : '',
    text_on: 'On',
    text_off: 'Off'
  }
}

test('CmkFormBooleanChoice renders value: checked', () => {
  const spec = getBooleanChoice(false)
  render(CmkFormBooleanChoice, {
    props: {
      spec,
      data: true,
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox')
  expect(checkbox.checked).toBe(true)
})

test('CmkFormBooleanChoice renders value: unchecked', () => {
  const spec = getBooleanChoice(true)
  render(CmkFormBooleanChoice, {
    props: {
      spec,
      data: false,
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox')
  expect(checkbox.checked).toBe(false)
})

test('CmkFormBooleanChoice toggle checkbox', () => {
  const spec = getBooleanChoice(true)
  render(CmkFormBooleanChoice, {
    props: {
      spec,
      data: false,
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox')
  checkbox.click()
  expect(checkbox.checked).toBe(true)
  checkbox.click()
  expect(checkbox.checked).toBe(false)
})
