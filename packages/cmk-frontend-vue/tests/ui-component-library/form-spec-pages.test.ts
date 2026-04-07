/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import UclFormAll from '@ucl/form/UclFormAll.vue'
import UclFormBinaryConditions from '@ucl/form/UclFormBinaryConditions.vue'
import UclFormBooleanChoice from '@ucl/form/UclFormBooleanChoice.vue'
import UclFormCascadingSingleChoice from '@ucl/form/UclFormCascadingSingleChoice.vue'
import UclFormCheckboxListChoice from '@ucl/form/UclFormCheckboxListChoice.vue'
import UclFormCommentTextArea from '@ucl/form/UclFormCommentTextArea.vue'
import UclFormConditionChoices from '@ucl/form/UclFormConditionChoices.vue'
import UclFormDataSize from '@ucl/form/UclFormDataSize.vue'
import UclFormDatePicker from '@ucl/form/UclFormDatePicker.vue'
import UclFormDictionary from '@ucl/form/UclFormDictionary.vue'
import UclFormDualListChoice from '@ucl/form/UclFormDualListChoice.vue'
import UclFormFixedValue from '@ucl/form/UclFormFixedValue.vue'
import UclFormFloat from '@ucl/form/UclFormFloat.vue'
import UclFormInteger from '@ucl/form/UclFormInteger.vue'
import UclFormList from '@ucl/form/UclFormList.vue'
import UclFormMetric from '@ucl/form/UclFormMetric.vue'
import UclFormMultilineText from '@ucl/form/UclFormMultilineText.vue'
import UclFormOptionalChoice from '@ucl/form/UclFormOptionalChoice.vue'
import UclFormPassword from '@ucl/form/UclFormPassword.vue'
import UclFormSimplePassword from '@ucl/form/UclFormSimplePassword.vue'
import UclFormSingleChoice from '@ucl/form/UclFormSingleChoice.vue'
import UclFormTimePicker from '@ucl/form/UclFormTimePicker.vue'
import UclFormTimeSpan from '@ucl/form/UclFormTimeSpan.vue'
import UclFormTuple from '@ucl/form/UclFormTuple.vue'

import { initializeComponentRegistry } from '@/form/private/FormEditDispatcher/dispatch'

beforeAll(() => {
  initializeComponentRegistry()
})

test.skip('FormAll demo page renders', () => {
  const { container } = render(UclFormAll, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormBooleanChoice demo page renders', () => {
  render(UclFormBooleanChoice, { props: { screenshotMode: false } })
  screen.getAllByRole('checkbox')
})

test('FormInteger demo page renders', () => {
  render(UclFormInteger, { props: { screenshotMode: false } })
  screen.getByRole('spinbutton')
})

test('FormFloat demo page renders', () => {
  render(UclFormFloat, { props: { screenshotMode: false } })
  screen.getByRole('spinbutton')
})

test('FormFixedValue demo page renders', () => {
  const { container } = render(UclFormFixedValue, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormCommentTextArea demo page renders', () => {
  render(UclFormCommentTextArea, { props: { screenshotMode: false } })
  screen.getByRole('textbox')
})

test('FormMultilineText demo page renders', () => {
  render(UclFormMultilineText, { props: { screenshotMode: false } })
  screen.getByRole('textbox')
})

test('FormDataSize demo page renders', () => {
  render(UclFormDataSize, { props: { screenshotMode: false } })
  screen.getByRole('spinbutton')
})

test('FormTimeSpan demo page renders', () => {
  render(UclFormTimeSpan, { props: { screenshotMode: false } })
  screen.getAllByRole('spinbutton')
})

test('FormCheckboxListChoice demo page renders', () => {
  render(UclFormCheckboxListChoice, { props: { screenshotMode: false } })
  screen.getAllByRole('checkbox')
})

test('FormPassword demo page renders', () => {
  const { container } = render(UclFormPassword, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormSimplePassword demo page renders', () => {
  const { container } = render(UclFormSimplePassword, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormDualListChoice demo page renders', () => {
  const { container } = render(UclFormDualListChoice, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormMetric demo page renders', () => {
  const { container } = render(UclFormMetric, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormTimePicker demo page renders', () => {
  const { container } = render(UclFormTimePicker, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormDatePicker demo page renders', () => {
  const { container } = render(UclFormDatePicker, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormDictionary demo page renders form elements', () => {
  render(UclFormDictionary, { props: { screenshotMode: false } })
  screen.getAllByRole('checkbox', { name: 'Service name' })
  screen.getAllByRole('checkbox', { name: 'Some string' })
})

test('FormList demo page renders', () => {
  render(UclFormList, { props: { screenshotMode: false } })
  screen.getByRole('button', { name: /add/i })
})

test('FormSingleChoice demo page renders', () => {
  render(UclFormSingleChoice, { props: { screenshotMode: false } })
  screen.getAllByRole('combobox')
})

test('FormCascadingSingleChoice demo page renders', () => {
  render(UclFormCascadingSingleChoice, { props: { screenshotMode: false } })
  screen.getAllByRole('combobox')
})

test('FormOptionalChoice demo page renders', () => {
  const { container } = render(UclFormOptionalChoice, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormTuple demo page renders', () => {
  const { container } = render(UclFormTuple, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormBinaryConditions demo page renders', () => {
  const { container } = render(UclFormBinaryConditions, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})

test('FormConditionChoices demo page renders', () => {
  const { container } = render(UclFormConditionChoices, { props: { screenshotMode: false } })
  expect(container.firstChild).toBeTruthy()
})
