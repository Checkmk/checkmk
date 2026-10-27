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

import { useFakeHostCheckResultsAction } from '@/monitoring/all-hosts/actions/fakeHostCheckResults'
import FakeCheckResultForm, {
  type FakeCheckResultValues
} from '@/monitoring/shared/components/action/actions/FakeCheckResultForm.vue'
import { useFakeServiceCheckResultsAction } from '@/monitoring/shared/components/action/actions/fakeServiceCheckResults'

const HOST = { name: 'db-1', site_id: 'local' }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

function mockFaked(faked: number): void {
  postSpy.mockResolvedValue({
    data: { faked },
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
}

beforeEach(() => {
  postSpy = vi.spyOn(client, 'POST')
  mockFaked(1)
})

test('starts from the good state without output or metrics', () => {
  expect(useFakeHostCheckResultsAction().defaultValues()).toEqual({
    state: 0,
    pluginOutput: '',
    metrics: ''
  })
})

test('says the check result was faked for the selected host', async () => {
  expect(
    await useFakeHostCheckResultsAction().perform([HOST], {
      state: 1,
      pluginOutput: '',
      metrics: ''
    })
  ).toEqual({ variant: 'success', message: 'Faked check result for the selected host' })
})

test('says the check results were faked for the selected services', async () => {
  mockFaked(2)

  expect(
    await useFakeServiceCheckResultsAction().perform(
      [
        { host: HOST, description: 'CPU load' },
        { host: HOST, description: 'Memory' }
      ],
      {
        state: 2,
        pluginOutput: '',
        metrics: ''
      }
    )
  ).toEqual({ variant: 'success', message: 'Faked check results for the selected services' })
})

test('reports a refused check result as an error', async () => {
  postSpy.mockResolvedValue({
    data: undefined,
    error: {},
    response: new Response(null, { status: 403 })
  } as never)

  expect(
    await useFakeHostCheckResultsAction().perform([HOST], {
      state: 1,
      pluginOutput: '',
      metrics: ''
    })
  ).toMatchObject({
    variant: 'error',
    heading: 'Could not fake the check results for the selected hosts'
  })
})

function renderForm(targetKind: 'host' | 'service') {
  const values = ref<FakeCheckResultValues>({ state: 0, pluginOutput: '', metrics: '' })
  const rendered = render(FakeCheckResultForm, {
    props: { targetKind, modelValue: values.value }
  })
  return { values, ...rendered }
}

test('offers a host the states of a host', () => {
  renderForm('host')

  expect(screen.getAllByRole('radio')).toHaveLength(2)
  expect(screen.getByRole('radio', { name: 'Down' })).toBeInTheDocument()
})

test('offers a service the states of a service', () => {
  renderForm('service')

  expect(screen.getAllByRole('radio')).toHaveLength(4)
  expect(screen.getByRole('radio', { name: 'Critical' })).toBeInTheDocument()
})

test('picking a result sets its state', async () => {
  const { values } = renderForm('service')

  await userEvent.click(screen.getByRole('radio', { name: 'Unknown' }))

  expect(values.value.state).toBe(3)
})

test('is valid without any input', () => {
  const { emitted } = renderForm('host')

  expect(emitted('update:valid')).toEqual([[true]])
})
