/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { computed, ref } from 'vue'

import MonitoringPagination from '@/monitoring/shared/components/MonitoringPagination.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

interface PageStub {
  first?: number
  last?: number
  matched?: number
  hasPrevious?: boolean
  hasNext?: boolean
}

function makeServiceStub({
  first = 1,
  last = 500,
  matched = 1247302,
  hasPrevious = false,
  hasNext = true
}: PageStub = {}) {
  return {
    pageFirst: computed(() => first),
    pageLast: computed(() => last),
    matched: ref(matched),
    hasPreviousPage: computed(() => hasPrevious),
    hasNextPage: computed(() => hasNext),
    nextPage: vi.fn(),
    previousPage: vi.fn()
  }
}

function renderPagination(stub: ReturnType<typeof makeServiceStub>, unit?: string) {
  return render(MonitoringPagination, {
    props: unit === undefined ? {} : { unit },
    global: {
      provide: { [MONITORING_SERVICE as symbol]: stub as unknown as MonitoringService<unknown> }
    }
  })
}

test('shows the page range with grouped exact positions', () => {
  renderPagination(makeServiceStub())

  expect(screen.getByText('1-500 of 1,247,302')).toBeInTheDocument()
})

test('appends the unit when one is given', () => {
  renderPagination(makeServiceStub(), 'flows')

  expect(screen.getByText('1-500 of 1,247,302 flows')).toBeInTheDocument()
})

test('renders nothing for a single-page listing', () => {
  const { container } = renderPagination(
    makeServiceStub({ last: 3, matched: 3, hasPrevious: false, hasNext: false })
  )

  expect(container.querySelector('.monitoring-pagination')).not.toBeInTheDocument()
})

test('disables the previous button on the first page', () => {
  renderPagination(makeServiceStub({ hasPrevious: false }))

  expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Next page' })).toBeEnabled()
})

test('disables the next button on the last page', () => {
  renderPagination(makeServiceStub({ hasPrevious: true, hasNext: false }))

  expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled()
})

test('steps the service through the pages', async () => {
  const stub = makeServiceStub({ hasPrevious: true, hasNext: true })
  renderPagination(stub)

  await userEvent.click(screen.getByRole('button', { name: 'Next page' }))
  expect(stub.nextPage).toHaveBeenCalledTimes(1)

  await userEvent.click(screen.getByRole('button', { name: 'Previous page' }))
  expect(stub.previousPage).toHaveBeenCalledTimes(1)
})
