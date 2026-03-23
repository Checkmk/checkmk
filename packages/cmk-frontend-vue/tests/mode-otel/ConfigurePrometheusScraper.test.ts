/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import ConfigurePrometheusScraper from '@/mode-otel/otel-configuration-steps/ConfigurePrometheusScraper.vue'

interface RenderOptions {
  jobName?: string
  metricsPath?: string
  address?: string
  port?: number | undefined
}

function renderComponent(options: RenderOptions = {}) {
  const {
    jobName: initialJobName = '',
    metricsPath: initialMetricsPath = '',
    address: initialAddress = '',
    port: initialPort = undefined
  } = options

  const jobName = ref(initialJobName)
  const metricsPath = ref(initialMetricsPath)
  const address = ref(initialAddress)
  const port = ref(initialPort)
  const compRef = ref<InstanceType<typeof ConfigurePrometheusScraper>>()

  render(
    defineComponent({
      components: { ConfigurePrometheusScraper },
      setup: () => ({ jobName, metricsPath, address, port, compRef }),
      template: `<ConfigurePrometheusScraper ref="compRef" v-model:job-name="jobName" v-model:metrics-path="metricsPath" v-model:address="address" v-model:port="port" />`
    })
  )

  return { jobName, metricsPath, address, port, compRef }
}

const VALID_INPUT: RenderOptions = {
  jobName: 'my_job',
  metricsPath: '/metrics',
  address: '192.168.1.1',
  port: 9090
}

describe('ConfigurePrometheusScraper', () => {
  afterEach(() => {
    cleanup()
  })

  test('does not show validation errors before validate() is called', () => {
    renderComponent()

    expect(screen.queryByText('Enter a name for your job.')).not.toBeInTheDocument()
    expect(
      screen.queryByText('Metrics path is required but not specified.')
    ).not.toBeInTheDocument()
    expect(screen.queryByText('Enter a valid IP address or host name.')).not.toBeInTheDocument()
    expect(screen.queryByText('Enter a valid port number (example: 1234).')).not.toBeInTheDocument()
  })

  test('validate() returns true when all required fields are valid', () => {
    const { compRef } = renderComponent(VALID_INPUT)

    const result = compRef.value!.validate()

    expect(result).toBe(true)
  })

  describe('job name validation', () => {
    test('shows error for empty job name', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, jobName: '' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Enter a name for your job.')
    })

    test('shows error for whitespace-only job name', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, jobName: '   ' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Enter a name for your job.')
    })
  })

  describe('metrics path validation', () => {
    test('shows error for empty metrics path', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, metricsPath: '' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Metrics path is required but not specified.')
    })

    test('shows error when metrics path does not start with /', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, metricsPath: 'metrics' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText("Metrics path must start with a '/'.")
    })

    test('accepts a multi-segment metrics path', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, metricsPath: '/metrics/custom' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })
  })

  describe('address validation', () => {
    test('shows error for empty address', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Enter a valid IP address or host name.')
    })

    test('shows error for whitespace-only address', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '   ' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Enter a valid IP address or host name.')
    })

    test('shows error for invalid hostname characters', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: 'host name!@#' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Your input is not a valid host name or IP address.')
    })

    test('accepts a valid IPv4 address', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '127.0.0.1' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('accepts 0.0.0.0', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '0.0.0.0' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('accepts IPv6 loopback ::1', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '::1' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('accepts IPv6 all interfaces ::', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '::' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('accepts a valid hostname', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: 'my-server.example.com' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('accepts localhost', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: 'localhost' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('accepts a full IPv6 address', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '2001:db8::1' })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('shows error for hostname starting with hyphen', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: '-invalid.com' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Your input is not a valid host name or IP address.')
    })

    test('shows error for hostname ending with hyphen', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, address: 'invalid-.com' })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Your input is not a valid host name or IP address.')
    })
  })

  describe('port validation', () => {
    test('shows error for missing port', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: undefined })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Enter a valid port number (example: 1234).')
    })

    test('shows error for non-integer port', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: 80.5 })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Port must be a whole number.')
    })

    test('shows error for port below 1', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: 0 })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Port must be between 1 and 65535.')
    })

    test('shows error for negative port', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: -1 })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Port must be between 1 and 65535.')
    })

    test('accepts port at lower boundary', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: 1 })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('accepts port at upper boundary', () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: 65535 })

      const result = compRef.value!.validate()

      expect(result).toBe(true)
    })

    test('shows error for port above 65535', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: 70000 })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Port must be between 1 and 65535.')
    })
  })

  test('shows all errors when all required fields are empty', async () => {
    const { compRef } = renderComponent()

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Enter a name for your job.')
    await screen.findByText('Metrics path is required but not specified.')
    await screen.findByText('Enter a valid IP address or host name.')
    await screen.findByText('Enter a valid port number (example: 1234).')
  })
})
