/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import FormTimeSpan from '@/form/components/forms/FormTimeSpan.vue'
import type { TimeSpan } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

function getSpec(
  displayedMagnitudes: TimeSpan['displayed_magnitudes'],
  validators: TimeSpan['validators']
): TimeSpan {
  return {
    type: 'time_span',
    title: 'utTitle',
    help: 'ut Help',
    displayed_magnitudes: displayedMagnitudes,
    validators: validators,
    label: 'utLabel',
    input_hint: null,
    i18n: {
      minute: 'ut_minute',
      second: 'ut_second',
      millisecond: 'ut_ms',
      hour: 'ut_h',
      day: 'ut_d',
      validation_negative_number: 'some negative error message'
    }
  }
}

test('FormTimeSpan renders value', () => {
  render(FormTimeSpan, {
    props: {
      spec: getSpec(['millisecond', 'second'], []),
      data: 66.6,
      backendValidation: []
    }
  })
  expect(screen.getByLabelText<HTMLInputElement>('ut_ms').value).toBe('600')
  expect(screen.getByLabelText<HTMLInputElement>('ut_second').value).toBe('66')
})

test('FormTimeSpan updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: getSpec(['minute', 'millisecond', 'second'], []),
    data: 66.6,
    backendValidation: []
  })

  const secondsInput = screen.getByLabelText<HTMLInputElement>('ut_second')
  const minutesInput = screen.getByLabelText<HTMLInputElement>('ut_minute')

  expect(screen.getByLabelText<HTMLInputElement>('ut_ms').value).toBe('600')
  expect(secondsInput.value).toBe('6')
  expect(minutesInput.value).toBe('1')

  expect(getCurrentData()).toMatch('66.6')
  await fireEvent.update(secondsInput, '200')
  expect(getCurrentData()).toMatch('260.6')
  await fireEvent.update(minutesInput, '2')
  expect(getCurrentData()).toMatch('320.6')
})

test('FormTimeSpan shows frontend validation', async () => {
  renderFormWithData({
    spec: getSpec(
      ['hour'],
      [
        {
          type: 'number_in_range',
          // value should be between 1 hour and 1 week
          min_value: 1 * 60 * 60,
          max_value: 7 * 24 * 60 * 60,
          error_message: 'some_error_message'
        }
      ]
    ),
    data: 2 * 60 * 60,
    backendValidation: []
  })

  const hoursInput = screen.getByLabelText<HTMLInputElement>('ut_h')
  await fireEvent.update(hoursInput, `${8 * 60 * 60}`)
  // there is not further value interpolation in the frontend: it just shows the error message of the backend
  screen.getByText('some_error_message')
})

test('FormTimeSpan shows error for negative values', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: getSpec(['hour', 'minute'], []),
    data: 1 * 60 * 60,
    backendValidation: []
  })

  const minutesInput = screen.getByLabelText<HTMLInputElement>('ut_minute')
  await fireEvent.update(minutesInput, '-1')

  expect(getCurrentData()).toMatch(`${1 * 60 * 60 - 60}`)
  screen.getByText('some negative error message')
})
