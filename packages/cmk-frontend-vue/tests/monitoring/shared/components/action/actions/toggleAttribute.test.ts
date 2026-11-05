/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'
import { ref } from 'vue'

import ToggleAttributeForm, {
  type ToggleAttributeValues
} from '@/monitoring/shared/components/action/actions/ToggleAttributeForm.vue'
import { useToggleHostAttributesActions } from '@/monitoring/shared/components/action/actions/toggleHostAttributes'
import { useToggleServiceAttributesActions } from '@/monitoring/shared/components/action/actions/toggleServiceAttributes'

const HOST = { name: 'db-1', site_id: 'local' }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

function mockModified(modified: number): void {
  postSpy.mockResolvedValue({
    data: { modified },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
}

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST')
  mockModified(1)
})

test('offers notifications, active and passive checks as the legacy commands', () => {
  expect(
    Object.values(useToggleHostAttributesActions()).map((action) => [
      action.id,
      action.title,
      action.formProps
    ])
  ).toEqual([
    ['notifications', 'Enable / Disable notifications', { label: 'Notifications' }],
    ['toggle_active_checks', 'Enable / Disable active checks', { label: 'Active checks' }],
    ['toggle_passive_checks', 'Enable / Disable passive checks', { label: 'Passive checks' }]
  ])
})

test('enables by default', () => {
  const { notifications } = useToggleHostAttributesActions()

  expect(notifications.defaultValues()).toEqual({ enabled: true })
})

test('says notifications were disabled for the selected host', async () => {
  const { notifications } = useToggleHostAttributesActions()

  expect(await notifications.perform([HOST], { enabled: false })).toEqual({
    variant: 'success',
    message: 'Disabled notifications for the selected host'
  })
  expect(postSpy.mock.lastCall[1].body).toMatchObject({
    attribute: 'notifications',
    enabled: false
  })
})

test('says passive checks were enabled for the selected services', async () => {
  mockModified(2)
  const passiveChecks = useToggleServiceAttributesActions().toggle_passive_checks

  expect(
    await passiveChecks.perform(
      [
        { host: HOST, description: 'CPU load' },
        { host: HOST, description: 'Memory' }
      ],
      { enabled: true }
    )
  ).toEqual({ variant: 'success', message: 'Enabled passive checks for the selected services' })
})

test('reports a refused change as an error', async () => {
  postSpy.mockResolvedValue({
    data: undefined,
    error: {},
    response: new Response(null, { status: 403 })
  } as never)
  const activeChecks = useToggleHostAttributesActions().toggle_active_checks

  expect(await activeChecks.perform([HOST], { enabled: false })).toMatchObject({
    variant: 'error',
    heading: 'Could not change the selected hosts'
  })
})

function renderForm() {
  const values = ref<ToggleAttributeValues>({ enabled: true })
  const rendered = render(ToggleAttributeForm, {
    props: { label: untranslated('Notifications'), modelValue: values.value }
  })
  return { values, ...rendered }
}

test('starts on "Enable"', () => {
  renderForm()

  expect(screen.getByRole('radio', { name: 'Enable' })).toBeChecked()
})

test('picking "Disable" disables', async () => {
  const { values } = renderForm()

  await userEvent.click(screen.getByRole('radio', { name: 'Disable' }))

  expect(values.value.enabled).toBe(false)
})

test('is valid without any input', () => {
  const { emitted } = renderForm()

  expect(emitted('update:valid')).toEqual([[true]])
})
