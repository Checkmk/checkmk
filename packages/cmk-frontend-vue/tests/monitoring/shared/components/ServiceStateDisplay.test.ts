/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import type { ServiceState } from '@/monitoring/shared/api/types'
import ServiceStateDisplay from '@/monitoring/shared/components/ServiceStateDisplay.vue'

test.each<[ServiceState, string]>([
  ['OK', 'OK'],
  ['WARN', 'WARNING'],
  ['CRIT', 'CRITICAL'],
  ['UNKNOWN', 'UNKNOWN']
])('renders the label for the %s state', (state, label) => {
  render(ServiceStateDisplay, { props: { state } })

  expect(screen.getByText(label)).toBeInTheDocument()
})

test.each<[ServiceState, string]>([
  ['OK', 'OK'],
  ['WARN', 'WA'],
  ['CRIT', 'CR'],
  ['UNKNOWN', 'UN']
])('abbreviates the %s state when inline', (state, label) => {
  render(ServiceStateDisplay, { props: { state, inline: true } })

  expect(screen.getByText(label)).toBeInTheDocument()
})

test('renders the pending label for the PENDING state', () => {
  render(ServiceStateDisplay, { props: { state: 'PENDING' } })

  expect(screen.getByText('PENDING')).toBeInTheDocument()
  expect(screen.queryByText('CRITICAL')).not.toBeInTheDocument()
})

test.each<[ServiceState, string, string]>([
  ['WARN', 'WA', 'Warning'],
  ['CRIT', 'CR', 'Critical'],
  ['UNKNOWN', 'UN', 'Unknown'],
  ['PENDING', 'PD', 'Pending']
])('spells out the abbreviated %s state on hover', (state, label, title) => {
  render(ServiceStateDisplay, { props: { state, abbreviated: true } })

  expect(screen.getByText(label)).toHaveAttribute('title', title)
})

test.each<[ServiceState, boolean, string]>([
  ['OK', true, 'OK'],
  ['WARN', false, 'WARNING']
])('shows no tooltip on the %s state when nothing is abbreviated', (state, abbreviated, label) => {
  render(ServiceStateDisplay, { props: { state, abbreviated } })

  expect(screen.getByText(label)).not.toHaveAttribute('title')
})
