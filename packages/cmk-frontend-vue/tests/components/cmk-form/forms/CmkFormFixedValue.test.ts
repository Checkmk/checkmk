import { render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/vue_formspec_components'
import FormFixedValue from '@/components/cmk-form/forms/FormFixedValue.vue'

function getFixedValue(withLabel = false): FormSpec.FixedValue {
  return {
    type: 'fixed_value',
    title: 'fooTitle',
    help: 'fooHelp',
    validators: [],
    label: withLabel ? 'fooLabel' : '',
    value: '42'
  }
}

test('FormFixedValue renders value', () => {
  const spec = getFixedValue(false)
  render(FormFixedValue, {
    props: {
      spec,
      data: 0,
      backendValidation: []
    }
  })

  screen.getByText('42')
})

test('FormFixedValue renders label', () => {
  const spec = getFixedValue(true)
  render(FormFixedValue, {
    props: {
      spec,
      data: 0,
      backendValidation: []
    }
  })

  screen.getByText('fooLabel')
})

test('FormFixedValue renders label, with nonsense data', () => {
  const spec = getFixedValue(true)
  render(FormFixedValue, {
    props: {
      spec,
      data: 'blabla nonsense',
      backendValidation: []
    }
  })

  screen.getByText('fooLabel')
})
