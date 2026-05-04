/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen } from '@testing-library/vue'

import PrometheusConfigurationSummary from '@/mode-otel/otel-configuration-steps/PrometheusConfigurationSummary.vue'

interface RenderProps {
  configName?: string
  siteId?: string
  jobName?: string
  metricsPath?: string
  address?: string
  port?: number
  encryption?: boolean
}

function renderSummary(props: RenderProps = {}) {
  const merged = {
    configName: 'prom_cfg_1',
    siteId: 'mysite',
    jobName: 'my_job',
    metricsPath: '/metrics',
    address: '10.0.0.1',
    port: 9090,
    encryption: false,
    ...props
  }
  render(PrometheusConfigurationSummary, { props: merged })
}

describe('PrometheusConfigurationSummary', () => {
  afterEach(() => {
    cleanup()
  })

  test('renders all rows with the supplied values', () => {
    renderSummary({
      configName: 'prom_cfg_1',
      siteId: 'mysite',
      jobName: 'my_job',
      metricsPath: '/metrics/custom',
      address: '10.0.0.1',
      port: 9090,
      encryption: false
    })

    expect(screen.getByText(/Configuration name/)).toBeInTheDocument()
    expect(screen.getByText(/prom_cfg_1/)).toBeInTheDocument()
    expect(screen.getByText(/Site/)).toBeInTheDocument()
    expect(screen.getByText(/mysite/)).toBeInTheDocument()
    expect(screen.getByText(/Job name/)).toBeInTheDocument()
    expect(screen.getByText(/my_job/)).toBeInTheDocument()
    expect(screen.getByText(/Metrics path/)).toBeInTheDocument()
    expect(screen.getByText(/\/metrics\/custom/)).toBeInTheDocument()
    expect(screen.getByText(/IP address or host name/)).toBeInTheDocument()
    expect(screen.getByText(/10\.0\.0\.1/)).toBeInTheDocument()
    expect(screen.getByText(/Port/)).toBeInTheDocument()
    expect(screen.getByText(/9090/)).toBeInTheDocument()
  })

  test('renders "TLS enabled" when encryption=true', () => {
    renderSummary({ encryption: true })

    expect(screen.getByText(/TLS enabled/)).toBeInTheDocument()
    expect(screen.queryByText(/No encryption/)).toBeNull()
  })

  test('renders "No encryption" when encryption=false', () => {
    renderSummary({ encryption: false })

    expect(screen.getByText(/No encryption/)).toBeInTheDocument()
    expect(screen.queryByText(/TLS enabled/)).toBeNull()
  })

  test('renders the Telemetry folder footnote', () => {
    renderSummary()

    expect(screen.getByText(/hosts will be created/)).toBeInTheDocument()
    expect(screen.getByText(/Telemetry/)).toBeInTheDocument()
  })

  test('renders the heading', () => {
    renderSummary()

    expect(screen.getByText(/Configuration details:/)).toBeInTheDocument()
  })
})
