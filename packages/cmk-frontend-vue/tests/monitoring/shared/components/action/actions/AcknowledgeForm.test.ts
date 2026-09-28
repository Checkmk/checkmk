/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getLocalTimeZone, now } from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { vi } from 'vitest'

import AcknowledgeForm, {
  type AcknowledgeValues
} from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'

function mountForm(
  overrides: Partial<AcknowledgeValues> = {},
  targetKind: 'host' | 'service' = 'host',
  links: { presetsUrl?: string | null; notificationRulesUrl?: string | null } = {}
) {
  const modelValue: AcknowledgeValues = {
    comment: '',
    expireOnEnabled: false,
    expireOn: null,
    sticky: false,
    persistent: false,
    notify: true,
    ...overrides
  }
  return render(AcknowledgeForm, { props: { modelValue, targetKind, ...links } })
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

  expect(
    screen.getByRole('checkbox', {
      name: 'Notify affected users if notification rules are in place (send notifications)'
    })
  ).toBeChecked()
  expect(
    screen.getByRole('checkbox', { name: 'Ignore status changes until the host recovers (OK/UP)' })
  ).not.toBeChecked()
  expect(
    screen.getByRole('checkbox', { name: 'Keep comment after acknowledgment expires' })
  ).not.toBeChecked()
})

test('the sticky option carries the example from the classic form', () => {
  mountForm()

  expect(
    screen.getByText("Service was WARN and goes CRIT - acknowledgment doesn't expire.")
  ).toBeInTheDocument()
})

test('links the options header to the presets only when the server offers the page', () => {
  const { unmount } = mountForm({}, 'host', { presetsUrl: 'wato.py?mode=edit_configvar' })

  expect(screen.getByText('Options')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '(Edit defaults)' })).toHaveAttribute(
    'href',
    'wato.py?mode=edit_configvar'
  )
  unmount()

  mountForm()
  expect(screen.getByText('Options')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '(Edit defaults)' })).not.toBeInTheDocument()
})

test('the notify option links the notification rules when the server names them', () => {
  mountForm({}, 'host', { notificationRulesUrl: 'wato.py?mode=notifications' })

  expect(screen.getByRole('link', { name: 'notification rules' })).toHaveAttribute(
    'href',
    'wato.py?mode=notifications'
  )
})

test('following the notification rules link leaves the notify option alone', async () => {
  // The link sits inside the checkbox's own <label>, where a click would otherwise reach the
  // control and silently flip the option while the tab opens.
  const { emitted } = mountForm({ notify: true }, 'host', {
    notificationRulesUrl: 'wato.py?mode=notifications'
  })

  const openTab = vi.spyOn(window, 'open').mockReturnValue(null)
  await userEvent.click(screen.getByRole('link', { name: 'notification rules' }))
  // The navigation is scripted, because cancelling the click is what stops the toggle.
  expect(openTab).toHaveBeenCalledWith('wato.py?mode=notifications', '_blank', 'noopener')
  openTab.mockRestore()

  expect(emitted('update:modelValue')).toBeUndefined()
  expect(
    screen.getByRole('checkbox', {
      name: 'Notify affected users if notification rules are in place (send notifications)'
    })
  ).toBeChecked()
})

test('both setup links open in a new tab, so a half-filled form survives the detour', () => {
  mountForm({}, 'host', {
    presetsUrl: 'wato.py?mode=edit_configvar',
    notificationRulesUrl: 'wato.py?mode=notifications'
  })

  // The notify link travels inside a translated label, so its target has to survive
  // the sanitizer CmkCheckbox pipes the label through.
  expect(screen.getByRole('link', { name: 'notification rules' })).toHaveAttribute(
    'target',
    '_blank'
  )
  expect(screen.getByRole('link', { name: '(Edit defaults)' })).toHaveAttribute('target', '_blank')
})

test('the sticky option names the service on the service page', () => {
  mountForm({}, 'service')

  expect(
    screen.getByRole('checkbox', { name: 'Ignore status changes until the service recovers (OK)' })
  ).toBeInTheDocument()
})

test('the expiry picker appears only once its checkbox is ticked', async () => {
  mountForm()

  const expireOn = screen.getByRole('checkbox', { name: 'Expire on' })
  expect(expireOn).not.toBeChecked()
  expect(screen.queryByLabelText('Date')).not.toBeInTheDocument()

  await userEvent.click(expireOn)
  expect(screen.getByLabelText('Date')).toBeInTheDocument()
})

test('ticking the expiry checkbox without a date turns the form invalid', async () => {
  const { emitted } = mountForm({ comment: 'on it' })

  expect(emitted('update:valid')?.at(-1)).toEqual([true])

  await userEvent.click(screen.getByRole('checkbox', { name: 'Expire on' }))
  expect(emitted('update:valid')?.at(-1)).toEqual([false])
})

test('an expiry date makes the form valid again', async () => {
  const { emitted } = mountForm({
    comment: 'on it',
    expireOnEnabled: true,
    expireOn: now(getLocalTimeZone())
  })

  expect(emitted('update:valid')?.at(-1)).toEqual([true])
})
