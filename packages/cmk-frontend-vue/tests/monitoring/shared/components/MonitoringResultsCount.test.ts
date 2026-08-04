/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MonitoringResultsCount from '@/monitoring/shared/components/MonitoringResultsCount.vue'

test('shows the matched row count when the results are narrowed', () => {
  render(MonitoringResultsCount, { props: { matched: 3, narrowed: true } })

  expect(screen.getByText('Rows matching your criteria: 3')).toBeInTheDocument()
})

test('shows no criteria text when nothing narrows the results', () => {
  render(MonitoringResultsCount, { props: { matched: 42, narrowed: false } })

  expect(screen.queryByText(/Rows matching your criteria/)).not.toBeInTheDocument()
})

test('keeps the line in the layout so the table does not jump', () => {
  const { container } = render(MonitoringResultsCount, {
    props: { matched: 42, narrowed: false }
  })

  expect(container.querySelector('.monitoring-results-count')).toBeInTheDocument()
})

test('shows no count when the criteria match no rows', () => {
  render(MonitoringResultsCount, { props: { matched: 0, narrowed: true } })

  expect(screen.queryByText(/Rows matching your criteria/)).not.toBeInTheDocument()
})

test('updates the count as the matched number changes', async () => {
  const { rerender } = render(MonitoringResultsCount, {
    props: { matched: 3, narrowed: true }
  })

  expect(screen.getByText('Rows matching your criteria: 3')).toBeInTheDocument()

  await rerender({ matched: 7, narrowed: true })
  expect(screen.getByText('Rows matching your criteria: 7')).toBeInTheDocument()
})
