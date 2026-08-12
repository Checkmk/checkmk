/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { vi } from 'vitest'
import { ref } from 'vue'

import MonitoringLimitSelector from '@/monitoring/shared/components/MonitoringLimitSelector.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import type { RequestedLimit } from '@/monitoring/shared/types'

function makeServiceStub(offeredLimits: RequestedLimit[]) {
  const requestedLimit = ref<RequestedLimit>(offeredLimits[0] ?? 1000)
  return {
    offeredLimits,
    requestedLimit,
    setRequestedLimit: vi.fn((value: RequestedLimit) => {
      requestedLimit.value = value
    })
  }
}

function renderSelector(stub: ReturnType<typeof makeServiceStub>) {
  return render(MonitoringLimitSelector, {
    global: {
      provide: { [MONITORING_SERVICE as symbol]: stub as unknown as MonitoringService<unknown> }
    }
  })
}

test('renders the current limit and offers a choice', () => {
  renderSelector(makeServiceStub([1000, 5000]))

  expect(screen.getByText('Show:')).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Row limit' })).toBeInTheDocument()
})

test('does not render when only a single limit is offered', () => {
  const { container } = renderSelector(makeServiceStub([1000]))

  expect(container.querySelector('.monitoring-limit-selector')).not.toBeInTheDocument()
})

test('offers the "All" option only when removing the limit is permitted', async () => {
  const user = userEvent.setup()
  renderSelector(makeServiceStub([1000, 5000, null]))

  await user.click(screen.getByRole('combobox', { name: 'Row limit' }))

  expect(await screen.findByRole('option', { name: 'All' })).toBeInTheDocument()
})

test('does not offer "All" when removing the limit is not permitted', async () => {
  const user = userEvent.setup()
  renderSelector(makeServiceStub([1000, 5000]))

  await user.click(screen.getByRole('combobox', { name: 'Row limit' }))

  expect(screen.queryByRole('option', { name: 'All' })).not.toBeInTheDocument()
})

test('switching the selection updates the requested limit', async () => {
  const user = userEvent.setup()
  const stub = makeServiceStub([1000, 5000, null])
  renderSelector(stub)

  await user.click(screen.getByRole('combobox', { name: 'Row limit' }))
  await user.click(await screen.findByRole('option', { name: '5000' }))

  expect(stub.setRequestedLimit).toHaveBeenCalledWith(5000)
})

test('selecting "All" requests the unlimited row limit', async () => {
  const user = userEvent.setup()
  const stub = makeServiceStub([1000, 5000, null])
  renderSelector(stub)

  await user.click(screen.getByRole('combobox', { name: 'Row limit' }))
  await user.click(await screen.findByRole('option', { name: 'All' }))

  expect(stub.setRequestedLimit).toHaveBeenCalledWith(null)
})
