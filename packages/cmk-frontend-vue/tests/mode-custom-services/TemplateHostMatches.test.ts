/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
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
  return render(TemplateHostMatches, {
    props: { preview, serviceName: 'HTTP duration', appendedAttributes: '+ http.route' }
  })
}

function isAlert(text: RegExp): boolean {
  return screen.getByText(text).closest('[role="alert"]') !== null
}

test('names the service and the hosts the template matches', () => {
  renderMatches({ status: 'resolved', resolution: RESOLUTION })

  expect(screen.getByText(/Service:/)).toHaveTextContent('Service: HTTP duration + http.route')
  expect(screen.getByText(/Target hosts:/)).toHaveTextContent(
    'Target hosts: pod-cart, pod-checkout'
  )
})

test('names resolved names that match no configured host apart', () => {
  renderMatches({
    status: 'resolved',
    resolution: { ...RESOLUTION, unmatched_host_names: ['pod-serach'] }
  })

  expect(screen.getByText(/Hosts that do not exist:/)).toHaveTextContent(
    'Hosts that do not exist: pod-serach'
  )
  expect(screen.getByText(/Target hosts:/)).not.toHaveTextContent('pod-serach')
})

test('warns that the service cannot be saved when no host matches', () => {
  renderMatches({ status: 'resolved', resolution: { ...RESOLUTION, matching_hosts: [] } })

  expect(isAlert(/No configured host currently matches/)).toBe(true)
  expect(screen.queryByText(/Service:/)).toBeNull()
  expect(screen.queryByText(/Target hosts:/)).toBeNull()
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

test('warns that truncated target hosts may be incomplete', () => {
  renderMatches({ status: 'resolved', resolution: { ...RESOLUTION, truncated: true } })

  expect(isAlert(/target hosts may be incomplete/)).toBe(true)
})

test('incomplete target hosts without a visible match are not reported as no match', () => {
  renderMatches({
    status: 'resolved',
    resolution: { ...RESOLUTION, matching_hosts: [], truncated: true }
  })

  expect(screen.getByText(/target hosts may be incomplete/)).toBeTruthy()
  expect(screen.queryByText(/No configured host currently matches/)).toBeNull()
})

test('shows a pending lookup instead of target hosts', () => {
  renderMatches({ status: 'loading' })

  expect(screen.getByText('Looking up the matching hosts…')).toBeTruthy()
  expect(screen.queryByText(/Target hosts:/)).toBeNull()
})

test('a failed lookup shows its reason and offers no refresh', () => {
  renderMatches({ status: 'failed', error: 'The data backend is not reachable.' })

  expect(screen.getByText('The data backend is not reachable.')).toBeTruthy()
  expect(screen.queryByRole('button')).toBeNull()
})

test('asks for a template before looking anything up', () => {
  renderMatches({ status: 'idle' })

  expect(screen.getByText(/Enter a host name template/)).toBeTruthy()
})

test('a refused template shows the reason', () => {
  renderMatches({
    status: 'refused',
    error: 'Host name template uses attributes the grouping drops'
  })

  expect(screen.getByText('Host name template uses attributes the grouping drops')).toBeTruthy()
})
