/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import type { HostState } from '@/monitoring/shared/api/types'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'

test.each<[HostState, string, string]>([
  ['DOWN', 'DO', 'Down'],
  ['UNREACHABLE', 'UN', 'Unreachable'],
  ['PENDING', 'PD', 'Pending']
])('spells out the abbreviated %s state on hover', (state, label, title) => {
  render(HostStateDisplay, { props: { state, abbreviated: true } })

  expect(screen.getByText(label)).toHaveAttribute('title', title)
})

test.each<[HostState, boolean, string]>([
  ['UP', true, 'UP'],
  ['DOWN', false, 'DOWN']
])('shows no tooltip on the %s state when nothing is abbreviated', (state, abbreviated, label) => {
  render(HostStateDisplay, { props: { state, abbreviated } })

  expect(screen.getByText(label)).not.toHaveAttribute('title')
})
