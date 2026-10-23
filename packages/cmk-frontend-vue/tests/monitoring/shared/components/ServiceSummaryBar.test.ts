/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import type { HostRef, ServiceCounts } from '@/monitoring/shared/api/types'
import ServiceSummaryBar from '@/monitoring/shared/components/ServiceSummaryBar.vue'

const COUNTS: ServiceCounts = { ok: 9, warn: 2, crit: 3, unknown: 1, pending: 0, total: 15 }

const HOST: HostRef = { site_id: 'local', name: 'web-1' }

test('gives every non-zero state a segment of the bar', async () => {
  render(ServiceSummaryBar, { props: { counts: COUNTS } })

  const bar = await screen.findByRole('img')
  expect(bar).toHaveAttribute('aria-label', '9 OK, 2 WARN, 3 CRIT, 1 UNKNOWN')

  // PENDING is 0 here, so it takes no width.
  expect(bar.querySelectorAll('.cmk-state-count-bar__segment')).toHaveLength(4)
})

test('legend lists every state with its count, including the zero one', async () => {
  render(ServiceSummaryBar, { props: { counts: COUNTS } })

  await screen.findByRole('img')

  for (const entry of ['OK: 9', 'WARN: 2', 'CRIT: 3', 'UNKNOWN: 1', 'PENDING: 0']) {
    expect(screen.getByText(entry)).toBeInTheDocument()
  }
})

test('handles a host whose services are all still pending', async () => {
  render(ServiceSummaryBar, {
    props: { counts: { ok: 0, warn: 0, crit: 0, unknown: 0, pending: 4, total: 4 } }
  })

  const bar = await screen.findByRole('img')
  expect(bar).toHaveAttribute('aria-label', '4 PENDING')
  expect(bar.querySelectorAll('.cmk-state-count-bar__segment')).toHaveLength(1)
})

test('leads with all services when a host is named, linking to its unfiltered page', async () => {
  render(ServiceSummaryBar, { props: { counts: COUNTS, host: HOST } })

  await screen.findByRole('img')

  const all = screen.getByRole('link', { name: 'All services: 15' })
  expect(all).toHaveAttribute('target', '_top')
  expect(all.getAttribute('href')).toContain('monitor_host_services.py')
  expect(all.getAttribute('href')).not.toContain('CRIT')
})

test('opens the host services page filtered to the state behind a non-zero count', async () => {
  render(ServiceSummaryBar, { props: { counts: COUNTS, host: HOST } })

  await screen.findByRole('img')

  const crit = screen.getByRole('link', { name: 'CRIT: 3' })
  expect(crit).toHaveAttribute('target', '_top')
  expect(crit.getAttribute('href')).toContain('monitor_host_services.py')
  expect(crit.getAttribute('href')).toContain('CRIT')
})

test('sends pending to the same host services page as every other state', async () => {
  render(ServiceSummaryBar, {
    props: { counts: { ok: 0, warn: 0, crit: 0, unknown: 0, pending: 4, total: 4 }, host: HOST }
  })

  await screen.findByRole('img')

  const pending = screen.getByRole('link', { name: 'PENDING: 4' })
  expect(pending.getAttribute('href')).toContain('monitor_host_services.py')
  expect(pending.getAttribute('href')).toContain('PENDING')
  expect(pending.getAttribute('href')).toContain('site=local')
})

test('a zero count is not linked', async () => {
  render(ServiceSummaryBar, { props: { counts: COUNTS, host: HOST } })

  await screen.findByRole('img')

  expect(screen.getByText('PENDING: 0')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: /PENDING/ })).not.toBeInTheDocument()
})

test('counts of a host that is not named lead nowhere', async () => {
  render(ServiceSummaryBar, { props: { counts: COUNTS } })

  await screen.findByRole('img')

  expect(screen.queryByText(/All services/)).not.toBeInTheDocument()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})
