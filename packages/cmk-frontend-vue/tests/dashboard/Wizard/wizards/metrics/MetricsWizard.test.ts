/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import MetricsWizard from '@/dashboard/components/Wizard/wizards/metrics/MetricsWizard.vue'
import { DashboardFeatures } from '@/dashboard/types/dashboard'
import { type ContextFilters, FilterOrigin } from '@/dashboard/types/filter'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { restAutocompleter } from '../../../../lib/autocompleters'

const HOST_AND_SERVICE: ConfiguredFilters = {
  host: { host: 'web01' },
  service: { service: 'CPU load' }
}

// The fake backend names its only metric after the host and service it was asked about.
useMswServer(
  restAutocompleter(({ parameters }) => {
    const context = parameters.context as ConfiguredFilters
    return [['util', `util of ${context.host?.host} / ${context.service?.service}`]]
  })
)

const asContextFilters = (filters: ConfiguredFilters): ContextFilters =>
  Object.fromEntries(
    Object.entries(filters).map(([name, configuredValues]) => [
      name,
      { configuredValues, source: FilterOrigin.DASHBOARD }
    ])
  )

const asWidgetSpec = (filters: ConfiguredFilters): WidgetSpec => ({
  content: {
    type: 'single_timeseries',
    metric: 'util',
    color: 'default_metric',
    timerange: 'dashboard'
  },
  filter_context: { filters, uses_infos: [] },
  general_settings: {
    title: { text: 'Graph', render_mode: 'with_background' },
    render_background: true
  }
})

function renderWizard(contextFilters: ContextFilters, editWidgetSpec: WidgetSpec | null) {
  render(
    defineComponent({
      setup() {
        useProvideFilterDefinitions({ definitions: {}, groups: {} })
        return () =>
          h(MetricsWizard, {
            tick: 0,
            range: {} as never,
            dashboardKey: { name: 'main', owner: '' },
            contextFilters,
            editWidgetSpec,
            dashboardFeatures: DashboardFeatures.UNRESTRICTED
          })
      }
    }),
    { global: { stubs: { SingleMultiWidgetObjectFilterConfiguration: true } } }
  )
}

describe('MetricsWizard metric selection', () => {
  beforeEach(() => {
    // Vue logs an "experimental feature" notice whenever <Suspense> renders, which fails the test.
    vi.spyOn(console, 'info').mockImplementation(() => {})
  })

  it.each([
    {
      origin: 'dashboard',
      contextFilters: asContextFilters(HOST_AND_SERVICE),
      editWidgetSpec: asWidgetSpec({})
    },
    {
      origin: 'widget',
      contextFilters: {},
      editWidgetSpec: asWidgetSpec(HOST_AND_SERVICE)
    }
  ])(
    'offers the metrics of the host and service set as $origin filters',
    async ({ contextFilters, editWidgetSpec }) => {
      renderWizard(contextFilters, editWidgetSpec)

      await userEvent.click(screen.getByRole('combobox', { name: 'Select service metric' }))

      expect(
        await screen.findByRole('option', { name: 'util of web01 / CPU load' })
      ).toBeInTheDocument()
    }
  )
})
