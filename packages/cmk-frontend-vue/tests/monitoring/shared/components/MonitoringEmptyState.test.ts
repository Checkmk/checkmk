/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { ref } from 'vue'

import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

function makeServiceStub(searchQuery = '') {
  return { searchQuery: ref(searchQuery) }
}

function renderEmptyState(stub: ReturnType<typeof makeServiceStub>) {
  return render(MonitoringEmptyState, {
    global: {
      provide: { [MONITORING_SERVICE as symbol]: stub as unknown as MonitoringService<unknown> }
    }
  })
}

test('shows the default message when there is no search query', () => {
  renderEmptyState(makeServiceStub(''))

  expect(screen.getByText('No results found.')).toBeInTheDocument()
  expect(
    screen.queryByText('Check for typing errors or try a broader term.')
  ).not.toBeInTheDocument()
})

test('shows the search-specific message and hint when a search query is set', () => {
  renderEmptyState(makeServiceStub('nonexistent-host'))

  expect(screen.getByText('No results found for your search.')).toBeInTheDocument()
  expect(screen.getByText('Check for typing errors or try a broader term.')).toBeInTheDocument()
})

test('reacts to the search query changing', async () => {
  const stub = makeServiceStub('')
  renderEmptyState(stub)

  expect(screen.getByText('No results found.')).toBeInTheDocument()

  stub.searchQuery.value = 'web'
  await screen.findByText('No results found for your search.')
})
