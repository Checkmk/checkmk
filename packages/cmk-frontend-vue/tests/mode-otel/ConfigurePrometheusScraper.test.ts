/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import ConfigurePrometheusScraper from '@/mode-otel/otel-configuration-steps/ConfigurePrometheusScraper.vue'

function renderComponent(initialJobName = '', initialPort: number | undefined = undefined) {
  const jobName = ref(initialJobName)
  const port = ref(initialPort)
  const compRef = ref<InstanceType<typeof ConfigurePrometheusScraper>>()

  render(
    defineComponent({
      components: { ConfigurePrometheusScraper },
      setup: () => ({ jobName, port, compRef }),
      template: `<ConfigurePrometheusScraper ref="compRef" v-model:job-name="jobName" v-model:port="port" />`
    })
  )

  return { jobName, port, compRef }
}

describe('ConfigurePrometheusScraper', () => {
  afterEach(() => {
    cleanup()
  })

  test('does not show validation errors before validate() is called', () => {
    renderComponent()

    expect(screen.queryByText('Enter a name for your job.')).not.toBeInTheDocument()
    expect(screen.queryByText('Port is required but not specified.')).not.toBeInTheDocument()
  })

  test('validate() returns false and shows error for empty job name', async () => {
    const { compRef } = renderComponent('', 9090)

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Enter a name for your job.')
  })

  test('validate() returns false and shows error for missing port', async () => {
    const { compRef } = renderComponent('my_job', undefined)

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Port is required but not specified.')
  })

  test('validate() returns false and shows both errors when both fields are empty', async () => {
    const { compRef } = renderComponent('', undefined)

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Enter a name for your job.')
    await screen.findByText('Port is required but not specified.')
  })

  test('validate() returns true when job name and port are provided', () => {
    const { compRef } = renderComponent('my_job', 9090)

    const result = compRef.value!.validate()

    expect(result).toBe(true)
  })

  test('validate() returns false for whitespace-only job name', async () => {
    const { compRef } = renderComponent('   ', 9090)

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Enter a name for your job.')
  })

  test('validate() returns false for non-integer port', async () => {
    const { compRef } = renderComponent('my_job', 80.5)

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Port must be a whole number.')
  })

  test('validate() returns false for port below 1', async () => {
    const { compRef } = renderComponent('my_job', 0)

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Port must be between 1 and 65535.')
  })

  test('validate() returns false for port above 65535', async () => {
    const { compRef } = renderComponent('my_job', 70000)

    const result = compRef.value!.validate()

    expect(result).toBe(false)
    await screen.findByText('Port must be between 1 and 65535.')
  })
})
