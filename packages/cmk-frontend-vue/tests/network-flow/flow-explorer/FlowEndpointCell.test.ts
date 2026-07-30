/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { expect, test, vi } from 'vitest'

import FlowEndpointCell from '@/network-flow/flow-explorer/components/FlowEndpointCell.vue'
import { autonomousSystemSlideInKey, hostSlideInKey } from '@/network-flow/slide-ins/injectionKeys'

const PROPS = { columnId: 'source_ip', address: '10.0.0.5', port: 54012, asn: 16509 }

function renderCell(openers: { host?: () => void; autonomousSystem?: () => void } = {}) {
  const provide: Record<symbol, unknown> = {}
  if (openers.host) {
    provide[hostSlideInKey as symbol] = openers.host
  }
  if (openers.autonomousSystem) {
    provide[autonomousSystemSlideInKey as symbol] = openers.autonomousSystem
  }
  return render(FlowEndpointCell, { props: PROPS, global: { provide } })
}

test('opens the host panel for the address', async () => {
  const host = vi.fn()
  renderCell({ host })

  // The accessible name describes the action and carries the visible text with
  // it; the title is left to the endpoint, so a truncated one reads on hover.
  await userEvent.click(screen.getByRole('button', { name: 'Show details of 10.0.0.5:54012' }))

  // The address, not the endpoint: the panel is about the host, not one of its ports.
  expect(host).toHaveBeenCalledWith('10.0.0.5')
})

test('opens the autonomous system panel for the ASN', async () => {
  const autonomousSystem = vi.fn()
  renderCell({ autonomousSystem })

  await userEvent.click(screen.getByRole('button', { name: /AS16509/ }))

  expect(autonomousSystem).toHaveBeenCalledWith(16509)
})

test('renders plain text where no panel is provided', () => {
  renderCell()

  expect(screen.queryByRole('button')).not.toBeInTheDocument()
  expect(screen.getByText('10.0.0.5:54012')).toBeInTheDocument()
})

test('the endpoint stays readable on hover, truncated or not', () => {
  renderCell({ host: vi.fn() })

  expect(screen.getByRole('button')).toHaveAttribute('title', '10.0.0.5:54012')
})

test('the autonomous system chip advertises no action without an opener', () => {
  renderCell()

  expect(screen.getByText('AS16509')).not.toHaveAttribute('title')
})
