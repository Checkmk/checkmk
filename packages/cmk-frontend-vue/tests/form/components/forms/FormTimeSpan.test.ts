import { fireEvent, render, screen } from '@testing-library/vue'
import FormTimeSpan from '@/form/components/forms/FormTimeSpan.vue'
import type { TimeSpan } from '@/form/components/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

function getSpec(displayedMagnitudes: TimeSpan['displayed_magnitudes']): TimeSpan {
  return {
    type: 'time_span',
    title: 'utTitle',
    help: 'ut Help',
    displayed_magnitudes: displayedMagnitudes,
    validators: [],
    i18n: {
      minute: 'ut_minute',
      second: 'ut_second',
      millisecond: 'ut_ms',
      hour: 'ut_h',
      day: 'ut_d'
    }
  }
}

test('FormTimeSpan renders value', () => {
  render(FormTimeSpan, {
    props: {
      spec: getSpec(['millisecond', 'second']),
      data: 66.6,
      backendValidation: []
    }
  })
  expect(screen.getByLabelText<HTMLInputElement>('ut_ms').value).toBe('600')
  expect(screen.getByLabelText<HTMLInputElement>('ut_second').value).toBe('66')
})

test('FormTimeSpan updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: getSpec(['minute', 'millisecond', 'second']),
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
