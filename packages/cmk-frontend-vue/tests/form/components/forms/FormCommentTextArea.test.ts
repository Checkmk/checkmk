/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'
import FormCommentTextArea from '@/form/components/forms/FormCommentTextArea.vue'

const validators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const spec: FormSpec.CommentTextArea = {
  type: 'comment_text_area',
  help: 'fooHelp',
  validators: validators,
  input_hint: 'fooInputHint',
  title: 'fooTitle',
  label: 'fooLabel',
  macro_support: false,
  monospaced: false,
  i18n: {
    prefix_date_and_comment: 'fooPrefixDateAndComment'
  },
  user_name: 'fooUserName'
}

test('FormCommentTextArea renders value', () => {
  render(FormCommentTextArea, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLTextAreaElement>('textbox')

  expect(element.value).toBe('fooData')
})

test('FormCommentTextArea updates data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec,
    data: 'fooData',
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(element, 'some_other_value')

  expect(getCurrentData()).toBe('"some_other_value"')
})

test('FormCommentTextArea checks validators', async () => {
  render(FormCommentTextArea, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('textbox')
  await fireEvent.update(element, '')
  screen.getByText('String length must be between 1 and 20')
})

test('FormCommentTextArea renders image/icon', () => {
  render(FormCommentTextArea, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLImageElement>('img')

  expect(element.alt).toBe('fooPrefixDateAndComment')
})

test('FormCommentTextArea on button click, adds username to the text', async () => {
  render(FormCommentTextArea, {
    props: {
      spec,
      data: 'fooData',
      backendValidation: []
    }
  })

  const button = screen.getByRole<HTMLImageElement>('img')
  await fireEvent.click(button)

  const text = screen.getByRole<HTMLTextAreaElement>('textbox')

  expect(text.value).toContain('fooUserName')
})
