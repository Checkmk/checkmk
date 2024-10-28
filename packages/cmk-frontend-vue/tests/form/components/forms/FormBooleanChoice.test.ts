/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import FormBooleanChoice from '@/form/components/forms/FormBooleanChoice.vue'

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

test('FormBooleanChoice renders value: checked', () => {
  const spec = getBooleanChoice(false)
  render(FormBooleanChoice, {
    props: {
      spec,
      data: true,
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox')
  expect(checkbox.checked).toBe(true)
})

test('FormBooleanChoice renders value: unchecked', () => {
  const spec = getBooleanChoice(true)
  render(FormBooleanChoice, {
    props: {
      spec,
      data: false,
      backendValidation: []
    }
  })

  const checkbox = screen.getByRole<HTMLInputElement>('checkbox')
  expect(checkbox.checked).toBe(false)
})

test('FormBooleanChoice toggle checkbox', () => {
  const spec = getBooleanChoice(true)
  render(FormBooleanChoice, {
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

test('FormBooleanChoice renders checkbox without label', () => {
  // With the absurd way of '::before'ing the checkbox we need to
  // make sure that the label exists in the DOM even if no label is passed
  const spec: FormSpec.BooleanChoice = {
    type: 'boolean_choice',
    title: '',
    help: '',
    validators: [],
    label: null,
    text_on: '',
    text_off: ''
  }
  render(FormBooleanChoice, {
    props: {
      spec,
      data: true,
      backendValidation: []
    }
  })

  screen.getByLabelText('')
})
