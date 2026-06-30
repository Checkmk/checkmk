/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import AcknowledgeForm, {
  type AcknowledgeValues
} from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'

function mountForm(overrides: Partial<AcknowledgeValues> = {}) {
  const modelValue: AcknowledgeValues = {
    comment: '',
    expireOn: null,
    sticky: false,
    persistent: false,
    notify: true,
    ...overrides
  }
  return render(AcknowledgeForm, { props: { modelValue } })
}

test('reports invalid while the comment is empty and valid once it is filled', async () => {
  const { emitted } = mountForm()

  expect(emitted('update:valid')?.at(-1)).toEqual([false])

  await userEvent.type(screen.getByPlaceholderText('Enter a comment…'), 'on it')
  expect(emitted('update:valid')?.at(-1)).toEqual([true])
})

test('whitespace-only comments stay invalid', async () => {
  const { emitted } = mountForm()

  await userEvent.type(screen.getByPlaceholderText('Enter a comment…'), '   ')
  expect(emitted('update:valid')?.at(-1)).toEqual([false])
})

test('notify is on by default and the option checkboxes are rendered', () => {
  mountForm()

  expect(screen.getByRole('checkbox', { name: 'Notify affected users' })).toBeChecked()
  expect(
    screen.getByRole('checkbox', { name: 'Ignore status changes until the host recovers (OK/UP)' })
  ).not.toBeChecked()
  expect(screen.getByRole('checkbox', { name: 'Persistent comment' })).not.toBeChecked()
})
