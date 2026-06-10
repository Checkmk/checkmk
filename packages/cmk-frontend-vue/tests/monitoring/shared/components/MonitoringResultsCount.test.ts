/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { ref } from 'vue'

import MonitoringResultsCount from '@/monitoring/shared/components/MonitoringResultsCount.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

function makeServiceStub(total = 0, searchQuery = '') {
  return { total: ref(total), searchQuery: ref(searchQuery) }
}

function renderCount(
  stub: ReturnType<typeof makeServiceStub>,
  props: { activeFilterCount?: number } = {}
) {
  return render(MonitoringResultsCount, {
    props,
    global: {
      provide: { [MONITORING_SERVICE as symbol]: stub as unknown as MonitoringService<unknown> }
    }
  })
}

test('shows the plain backend total when nothing narrows the results', () => {
  renderCount(makeServiceStub(42))

  expect(screen.getByText('Rows found: 42')).toBeInTheDocument()
})

test('uses the same wording for a single match', () => {
  renderCount(makeServiceStub(1))

  expect(screen.getByText('Rows found: 1')).toBeInTheDocument()
})

test('shows no count text when there are no matches', () => {
  renderCount(makeServiceStub(0))

  expect(screen.queryByText('Rows found: 0')).not.toBeInTheDocument()
})

test('shows no count text when a search yields no matches', () => {
  renderCount(makeServiceStub(0, 'web'))

  expect(screen.queryByText('Rows matching your search: 0')).not.toBeInTheDocument()
})

test('keeps the line in the layout so the table does not jump', () => {
  const { container } = renderCount(makeServiceStub(0))

  expect(container.querySelector('.monitoring-results-count')).toBeInTheDocument()
})

test('reacts to the total changing', async () => {
  const stub = makeServiceStub(2)
  renderCount(stub)

  expect(screen.getByText('Rows found: 2')).toBeInTheDocument()

  stub.total.value = 5
  await screen.findByText('Rows found: 5')
})

test('names the search when only a search is active', () => {
  renderCount(makeServiceStub(3, 'web'))

  expect(screen.getByText('Rows matching your search: 3')).toBeInTheDocument()
})

test('uses the singular filter wording for a single active filter', () => {
  renderCount(makeServiceStub(3), { activeFilterCount: 1 })

  expect(screen.getByText('Rows matching your filter: 3')).toBeInTheDocument()
})

test('pluralizes the filter wording for multiple active filters', () => {
  renderCount(makeServiceStub(3), { activeFilterCount: 2 })

  expect(screen.getByText('Rows matching your filters: 3')).toBeInTheDocument()
})

test('names both when a single filter and a search are active', () => {
  renderCount(makeServiceStub(2, 'web'), { activeFilterCount: 1 })

  expect(screen.getByText('Rows matching your filter and search: 2')).toBeInTheDocument()
})

test('pluralizes filters when multiple filters and a search are active', () => {
  renderCount(makeServiceStub(2, 'web'), { activeFilterCount: 3 })

  expect(screen.getByText('Rows matching your filters and search: 2')).toBeInTheDocument()
})
