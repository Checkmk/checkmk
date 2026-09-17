/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

import FormStaticText from '@/form/private/forms/FormStaticText.vue'

const PENDING_TEXT = 'The URL will be generated automatically after you save the form.'

function getStaticText(overrides: Partial<FormSpec.StaticText> = {}): FormSpec.StaticText {
  return {
    type: 'static_text',
    title: 'fooTitle',
    help: 'fooHelp',
    validators: [],
    value: '',
    style: 'text',
    ...overrides
  }
}

test('FormStaticText renders the placeholder in an info alert when the value is empty', () => {
  render(FormStaticText, {
    props: {
      spec: getStaticText({ placeholder: PENDING_TEXT }),
      data: '',
      backendValidation: []
    }
  })

  expect(screen.getByRole('status').textContent).toContain(PENDING_TEXT)
})

test('FormStaticText placeholder renders as info box even for alert styles', () => {
  render(FormStaticText, {
    props: {
      spec: getStaticText({ style: 'alert_error', placeholder: PENDING_TEXT }),
      data: '',
      backendValidation: []
    }
  })

  expect(screen.getByRole('status').textContent).toContain(PENDING_TEXT)
  expect(screen.queryByRole('alert')).toBeNull()
})

test('FormStaticText prefers the value over the placeholder', () => {
  render(FormStaticText, {
    props: {
      spec: getStaticText({ placeholder: PENDING_TEXT }),
      data: 'https://remote/check_mk/saml_acs.py?acs',
      backendValidation: []
    }
  })

  screen.getByText('https://remote/check_mk/saml_acs.py?acs')
  expect(screen.queryByText(PENDING_TEXT)).toBeNull()
  expect(screen.queryByRole('status')).toBeNull()
})

test('FormStaticText without placeholder renders an empty value as empty text', () => {
  const { container } = render(FormStaticText, {
    props: {
      spec: getStaticText(),
      data: '',
      backendValidation: []
    }
  })

  expect(screen.queryByRole('status')).toBeNull()
  const label = container.querySelector('label')
  expect(label).not.toBeNull()
  expect(label!.textContent).toBe('')
})
