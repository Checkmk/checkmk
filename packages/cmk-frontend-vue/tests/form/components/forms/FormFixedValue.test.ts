/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormFixedValue from '@/form/components/forms/FormFixedValue.vue'

function getFixedValue(withLabel = false): FormSpec.FixedValue {
  const spec: FormSpec.FixedValue = {
    type: 'fixed_value',
    title: 'fooTitle',
    help: 'fooHelp',
    validators: [],
    value: '42',
    label: null
  }
  if (withLabel) {
    spec['label'] = 'fooLabel'
  }

  return spec
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
