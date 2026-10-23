/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import TemplateHostMatches from '@/mode-custom-services/steps/TemplateHostMatches.vue'
import type { TemplatePreview } from '@/mode-custom-services/templatePreview'

const RESOLUTION = {
  matching_hosts: ['pod-cart', 'pod-checkout'],
  unmatched_host_names: [],
  hidden_match_count: 0,
  truncated: false
}

function renderMatches(preview: TemplatePreview) {
  return render(TemplateHostMatches, { props: { preview } })
}

function isAlert(text: RegExp): boolean {
  return screen.getByText(text).closest('[role="alert"]') !== null
}

test('lists the hosts the template matches', () => {
  renderMatches({ status: 'resolved', resolution: RESOLUTION })

  expect(screen.getByText(/Matching hosts/)).toHaveTextContent('(2)')
  expect(screen.getByText('pod-cart')).toBeTruthy()
  expect(screen.getByText('pod-checkout')).toBeTruthy()
})

test('lists resolved names that match no configured host apart', () => {
  renderMatches({
    status: 'resolved',
    resolution: { ...RESOLUTION, unmatched_host_names: ['pod-serach'] }
  })

  expect(screen.getByText(/without a configured host/)).toHaveTextContent('(1)')
  expect(screen.getByText('pod-serach')).toBeTruthy()
})

test('warns that the service cannot be saved when no host matches', () => {
  renderMatches({ status: 'resolved', resolution: { ...RESOLUTION, matching_hosts: [] } })

  expect(isAlert(/No configured host currently matches/)).toBe(true)
})

test('warns about matching hosts the user may not see', () => {
  renderMatches({ status: 'resolved', resolution: { ...RESOLUTION, hidden_match_count: 2 } })

  expect(isAlert(/2 matching hosts are in folders you may not see/)).toBe(true)
})

test('matches that are all hidden are not reported as no match', () => {
  renderMatches({
    status: 'resolved',
    resolution: { ...RESOLUTION, matching_hosts: [], hidden_match_count: 3 }
  })

  expect(screen.getByText(/3 matching hosts are in folders you may not see/)).toBeTruthy()
  expect(screen.queryByText(/No configured host currently matches/)).toBeNull()
})

test('warns that a truncated list is incomplete', () => {
  renderMatches({ status: 'resolved', resolution: { ...RESOLUTION, truncated: true } })

  expect(isAlert(/this list is incomplete/)).toBe(true)
})

test('an incomplete list without a visible match is not reported as no match', () => {
  renderMatches({
    status: 'resolved',
    resolution: { ...RESOLUTION, matching_hosts: [], truncated: true }
  })

  expect(screen.getByText(/this list is incomplete/)).toBeTruthy()
  expect(screen.queryByText(/No configured host currently matches/)).toBeNull()
})

test('shows a pending lookup instead of a list', () => {
  renderMatches({ status: 'loading' })

  expect(screen.getByText('Looking up the matching hosts…')).toBeTruthy()
  expect(screen.queryByRole('list')).toBeNull()
})

test('a failed lookup shows its reason and can be retried', async () => {
  const { emitted } = renderMatches({
    status: 'failed',
    error: 'The data backend is not reachable.'
  })

  expect(screen.getByText('The data backend is not reachable.')).toBeTruthy()
  await userEvent.click(screen.getByRole('button', { name: 'Refresh' }))
  expect(emitted('refresh')).toHaveLength(1)
})

test('asks for a template before looking anything up', () => {
  renderMatches({ status: 'idle' })

  expect(screen.getByText(/Enter a host name template/)).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Refresh' })).toBeDisabled()
})

test('a refused template shows the reason', () => {
  renderMatches({
    status: 'refused',
    error: 'Host name template uses attributes the grouping drops'
  })

  expect(screen.getByText('Host name template uses attributes the grouping drops')).toBeTruthy()
})
