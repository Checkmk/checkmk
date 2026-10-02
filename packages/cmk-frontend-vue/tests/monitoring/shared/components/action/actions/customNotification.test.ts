/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, expect, test, vi } from 'vitest'
import { ref } from 'vue'

import CustomNotificationForm, {
  type CustomNotificationValues
} from '@/monitoring/shared/components/action/actions/CustomNotificationForm.vue'
import { useNotifyHostsAction } from '@/monitoring/shared/components/action/actions/notifyHosts'
import { useNotifyServicesAction } from '@/monitoring/shared/components/action/actions/notifyServices'

const HOST = { name: 'db-1', site_id: 'local' }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
    data: { notified: 1 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
})

test('starts with an empty comment and neither forced nor broadcast', () => {
  expect(useNotifyHostsAction().defaultValues()).toEqual({
    comment: '',
    forced: false,
    broadcast: false
  })
})

test('says the notifications were sent for the selected host', async () => {
  const action = useNotifyHostsAction()

  expect(
    await action.perform([HOST], { comment: 'Testing', forced: false, broadcast: true })
  ).toEqual({
    variant: 'success',
    message: 'Sent custom notifications for the selected host'
  })
  expect(postSpy.mock.lastCall[1].body).toMatchObject({ comment: 'Testing', broadcast: true })
})

test('says the notifications were sent for the selected services', async () => {
  postSpy.mockResolvedValue({
    data: { notified: 2 },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
  const action = useNotifyServicesAction()

  expect(
    await action.perform(
      [
        { host: HOST, description: 'CPU load' },
        { host: HOST, description: 'Memory' }
      ],
      {
        comment: 'Testing',
        forced: true,
        broadcast: false
      }
    )
  ).toEqual({ variant: 'success', message: 'Sent custom notifications for the selected services' })
})

test('reports a refused notification as an error', async () => {
  postSpy.mockResolvedValue({
    data: undefined,
    error: {},
    response: new Response(null, { status: 403 })
  } as never)

  expect(
    await useNotifyHostsAction().perform([HOST], {
      comment: 'Testing',
      forced: false,
      broadcast: false
    })
  ).toMatchObject({
    variant: 'error',
    heading: 'Could not send the custom notifications for the selected hosts'
  })
})

test('the form is valid only with a comment', async () => {
  const values = ref<CustomNotificationValues>({ comment: '', forced: false, broadcast: false })
  const { emitted } = render(CustomNotificationForm, {
    props: {
      targetKind: 'host',
      modelValue: values.value,
      'onUpdate:modelValue': (value: CustomNotificationValues) => (values.value = value)
    }
  })

  await userEvent.type(screen.getByPlaceholderText('Enter your message here'), '  ')
  expect(emitted('update:valid')!.at(-1)).toEqual([false])

  await userEvent.type(screen.getByPlaceholderText('Enter your message here'), 'Testing')
  expect(emitted('update:valid')!.at(-1)).toEqual([true])
})

test('points out a missing comment once asked to show errors, until one is typed', async () => {
  render(CustomNotificationForm, {
    props: {
      targetKind: 'host',
      modelValue: { comment: '', forced: false, broadcast: false },
      showErrors: true
    }
  })
  expect(screen.getByText('Comment is required.')).toBeInTheDocument()

  await userEvent.type(screen.getByPlaceholderText('Enter your message here'), 'Testing')
  expect(screen.queryByText('Comment is required.')).not.toBeInTheDocument()
})

test('names the contacts of the selected services for a service', () => {
  render(CustomNotificationForm, {
    props: {
      targetKind: 'service',
      modelValue: { comment: '', forced: false, broadcast: false }
    }
  })

  expect(
    screen.getByRole('checkbox', {
      name: 'Send to all contacts of the selected services (broadcast)'
    })
  ).toBeInTheDocument()
})
