import { render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/vue_formspec_components'
import CmkFormFixedValue from '@/components/cmk-form/element/CmkFormFixedValue.vue'

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

test('CmkFormFixedValue renders value', () => {
  const spec = getFixedValue(false)
  render(CmkFormFixedValue, {
    props: {
      spec,
      data: 0,
      backendValidation: []
    }
  })

  screen.getByText('42')
})

test('CmkFormFixedValue renders label', () => {
  const spec = getFixedValue(true)
  render(CmkFormFixedValue, {
    props: {
      spec,
      data: 0,
      backendValidation: []
    }
  })

  screen.getByText('fooLabel')
})

test('CmkFormFixedValue renders label, with nonsense data', () => {
  const spec = getFixedValue(true)
  render(CmkFormFixedValue, {
    props: {
      spec,
      data: 'blabla nonsense',
      backendValidation: []
    }
  })

  screen.getByText('fooLabel')
})
