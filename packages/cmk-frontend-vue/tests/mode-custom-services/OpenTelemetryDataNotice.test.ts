/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import type { HostOpenTelemetryData } from '@/mode-custom-services/definition'
import type { OpenTelemetryData } from '@/mode-custom-services/openTelemetryData'
import OpenTelemetryDataNotice from '@/mode-custom-services/steps/OpenTelemetryDataNotice.vue'

function renderNotice(data: OpenTelemetryData) {
  return render(OpenTelemetryDataNotice, { props: { data } })
}

function host(
  hostName: string,
  state: HostOpenTelemetryData['opentelemetry_data'],
  dcdConnection: HostOpenTelemetryData['dcd_connection'] = null
): HostOpenTelemetryData {
  return { host_name: hostName, opentelemetry_data: state, dcd_connection: dcdConnection }
}

test('names the hosts saving enables OpenTelemetry data on', () => {
  renderNotice({
    status: 'loaded',
    hosts: [host('pod-cart', 'to_enable'), host('pod-search', 'enabled')]
  })

  expect(screen.getByRole('status')).toHaveTextContent(
    'OpenTelemetry data will be enabled on pod-cart when you save.'
  )
})

test('says nothing about hosts that already have OpenTelemetry data enabled', () => {
  renderNotice({ status: 'loaded', hosts: [host('pod-cart', 'enabled')] })

  expect(screen.queryByText(/OpenTelemetry data/)).toBeNull()
})

test('warns about a host whose OpenTelemetry data a DCD connection keeps disabled', () => {
  renderNotice({
    status: 'loaded',
    hosts: [host('pod-cart', 'locked', { id: 'piggyback', title: 'Piggyback hosts' })]
  })

  expect(screen.getByRole('alert')).toHaveTextContent(
    'OpenTelemetry data is disabled on pod-cart by the dynamic host management connection "Piggyback hosts", so this service will not receive data on that host. Enable OpenTelemetry data in that connection.'
  )
})

test('warns about a host whose OpenTelemetry data is locked without a DCD connection', () => {
  renderNotice({ status: 'loaded', hosts: [host('pod-cart', 'locked')] })

  expect(screen.getByRole('alert')).toHaveTextContent(
    'OpenTelemetry data is disabled and locked on pod-cart, so this service will not receive data on that host.'
  )
})

test('warns once per locked host', () => {
  renderNotice({
    status: 'loaded',
    hosts: [host('pod-cart', 'locked'), host('pod-search', 'locked')]
  })

  expect(screen.getAllByRole('alert')).toHaveLength(2)
})

test('says when the hosts could not be checked', () => {
  renderNotice({ status: 'failed' })

  expect(screen.getByRole('alert')).toHaveTextContent(
    'Could not check whether OpenTelemetry data is enabled on the hosts.'
  )
})
