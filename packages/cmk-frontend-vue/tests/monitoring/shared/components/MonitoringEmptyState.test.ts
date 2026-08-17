/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'

test('shows the default message when there is no search query or active filter', () => {
  render(MonitoringEmptyState)

  expect(screen.getByText('No results found.')).toBeInTheDocument()
  expect(
    screen.queryByText('Check for typing errors or try a broader term.')
  ).not.toBeInTheDocument()
})

test('shows the search-specific message and hint when a search query is set', () => {
  render(MonitoringEmptyState, { props: { hasSearchQuery: true } })

  expect(screen.getByText('No results found for your search.')).toBeInTheDocument()
  expect(
    screen.getByText('Check for typing errors, try using wildcards or a broader term.')
  ).toBeInTheDocument()
})

test('shows the filter-specific message and hint when only a filter is active', () => {
  render(MonitoringEmptyState, { props: { hasActiveFilter: true } })

  expect(screen.getByText('No results found for your active filters.')).toBeInTheDocument()
  expect(screen.getByText('Remove one or more filters to widen the results.')).toBeInTheDocument()
})

test('shows the combined message and hint when both a filter and a search are active', () => {
  render(MonitoringEmptyState, { props: { hasSearchQuery: true, hasActiveFilter: true } })

  expect(
    screen.getByText('No results for your combination of search and filter settings.')
  ).toBeInTheDocument()
  expect(screen.getByText('Adjust or clear search and filters to start fresh.')).toBeInTheDocument()
})

test('reacts to the search query becoming set', async () => {
  const { rerender } = render(MonitoringEmptyState, { props: { hasSearchQuery: false } })

  expect(screen.getByText('No results found.')).toBeInTheDocument()

  await rerender({ hasSearchQuery: true })
  expect(screen.getByText('No results found for your search.')).toBeInTheDocument()
})
