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
  port?: number | undefined
}

function renderComponent(options: RenderOptions = {}) {
  const {
    jobName: initialJobName = '',
    metricsPath: initialMetricsPath = '',
    port: initialPort = undefined
  } = options

  const jobName = ref(initialJobName)
  const metricsPath = ref(initialMetricsPath)
  const port = ref(initialPort)
  const compRef = ref<InstanceType<typeof ConfigurePrometheusScraper>>()

  render(
    defineComponent({
      components: { ConfigurePrometheusScraper },
      setup: () => ({ jobName, metricsPath, port, compRef }),
      template: `<ConfigurePrometheusScraper ref="compRef" v-model:job-name="jobName" v-model:metrics-path="metricsPath" v-model:port="port" />`
    })
  )

  return { jobName, metricsPath, port, compRef }
}

const VALID_INPUT: RenderOptions = {
  jobName: 'my_job',
  metricsPath: '/metrics',
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
    expect(screen.queryByText('Port is required but not specified.')).not.toBeInTheDocument()
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

  describe('port validation', () => {
    test('shows error for missing port', async () => {
      const { compRef } = renderComponent({ ...VALID_INPUT, port: undefined })

      const result = compRef.value!.validate()

      expect(result).toBe(false)
      await screen.findByText('Port is required but not specified.')
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
    await screen.findByText('Port is required but not specified.')
  })
})
