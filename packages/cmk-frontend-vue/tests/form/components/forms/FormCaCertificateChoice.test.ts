/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

import FormCaCertificateChoice from '@/form/private/forms/FormCaCertificateChoice.vue'

const spec: FormSpec.CaCertificateChoice = {
  type: 'ca_certificate_choice',
  title: 'Inherited from global settings',
  help: '',
  validators: [],
  elements: [
    { value: 'CA one', label: null, detail_groups: [[{ title: 'Subject', text: 'CN=one' }]] },
    { value: 'CA two', label: null, detail_groups: [[{ title: 'Subject', text: 'CN=two' }]] }
  ],
  chosen_label: 'Trusted',
  not_chosen_label: 'Not trusted'
}

function renderChoice(data: unknown[]): unknown[][] {
  const updates: unknown[][] = []
  render(FormCaCertificateChoice, {
    props: {
      spec,
      data,
      backendValidation: [],
      'onUpdate:data': (value: unknown[]) => updates.push(value)
    }
  })
  return updates
}

test('FormCaCertificateChoice shows each certificate as trusted or not', () => {
  renderChoice(['CA two'])
  expect(screen.getAllByRole('cell').map((cell) => cell.textContent)).toEqual(
    expect.arrayContaining(['Not trusted:', 'CN=one', 'Trusted:', 'CN=two'])
  )
})

test('FormCaCertificateChoice keeps the certificate order when one is chosen', async () => {
  const updates = renderChoice(['CA two'])
  screen.getAllByRole('checkbox')[0]!.click()
  await waitFor(() => expect(updates).toEqual([['CA one', 'CA two']]))
})

test('FormCaCertificateChoice drops a certificate that is no longer chosen', async () => {
  const updates = renderChoice(['CA one', 'CA two'])
  screen.getAllByRole('checkbox')[1]!.click()
  await waitFor(() => expect(updates).toEqual([['CA one']]))
})
