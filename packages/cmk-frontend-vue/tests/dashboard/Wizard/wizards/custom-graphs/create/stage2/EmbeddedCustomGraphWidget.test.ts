/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { useEmbeddedCustomGraph } from '@/dashboard/components/Wizard/wizards/custom-graphs/create/composables/useEmbeddedCustomGraph'
import EmbeddedCustomGraphWidget from '@/dashboard/components/Wizard/wizards/custom-graphs/create/stage2/EmbeddedCustomGraphWidget.vue'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

const CONSTANTS = {
  responsive_grid_breakpoints: {},
  widgets: { embedded_custom_graph: { filter_context: { restricted_to_single: [] } } }
} as unknown as DashboardConstants

const DISCOVER_PATH = '/domain-types/graph/actions/discover_custom_graphs/invoke'
const WIDGET_ATTRIBUTES_PATH = '/domain-types/dashboard/actions/compute-widget-attributes/invoke'
const WIDGET_TITLES_PATH = '/domain-types/dashboard/actions/compute-widget-titles/invoke'

const RRD_SOURCE = {
  type: 'rrd_metric',
  id: 'A',
  title: 'CPU',
  line_type: 'line',
  mirrored: false,
  visible: true,
  color: '#28a2f3',
  host_name: 'my-host',
  service_name: 'CPU utilization',
  metric_name: 'util',
  consolidation: 'avg'
}

const STORED_WIDGET = {
  content: {
    type: 'embedded_custom_graph',
    definition: {
      data_sources: [RRD_SOURCE],
      graph_options: {
        unit: { type: 'first_entry_with_unit' },
        explicit_vertical_range: { type: 'auto' },
        omit_zero_metrics: false
      }
    },
    timerange: { type: 'graph', duration: 4 * 3600 },
    graph_render_options: {}
  },
  filter_context: { filters: {}, uses_infos: [] },
  general_settings: {
    title: { text: 'My graph', render_mode: 'with_background' },
    render_background: true
  }
} as unknown as WidgetSpec

type DiscoverBody = {
  definition: {
    data_sources: { id: string }[]
    graph_options: { omit_zero_metrics: boolean }
  }
}

function ok(data: unknown): never {
  return { data, error: undefined, response: new Response(null, { status: 200 }) } as never
}

let postSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  vi.spyOn(client, 'GET').mockImplementation(async () =>
    ok({ value: [{ title: 'Last 4 hours', extensions: { total_seconds: 4 * 3600 } }] })
  )
  postSpy = vi
    .spyOn(client, 'POST')
    .mockImplementation(async (path: unknown) =>
      ok(
        path === WIDGET_ATTRIBUTES_PATH
          ? { value: { filter_context: { uses_infos: [] } } }
          : path === WIDGET_TITLES_PATH
            ? { extensions: { titles: {} } }
            : { graphs: [] }
      )
    )
})

function discoverBodies(): DiscoverBody[] {
  return postSpy.mock.calls
    .filter(([path]: unknown[]) => path === DISCOVER_PATH)
    .map(([, options]: unknown[]) => (options as { body: DiscoverBody }).body)
}

function renderWidget(spec: WidgetSpec | null = STORED_WIDGET) {
  const consumer = defineComponent({
    setup() {
      const handler = useEmbeddedCustomGraph(spec)
      return () =>
        h(EmbeddedCustomGraphWidget, {
          handler,
          dashboardKey: { name: 'main', owner: '' },
          tick: 0,
          range: makeContentProps(null).range,
          filters: {}
        })
    }
  })
  render(
    defineComponent({
      setup() {
        useProvideDashboardConstants(CONSTANTS)
        useProvideMissingRuntimeFiltersAction(ref(true), () => {})
        return () => h(consumer)
      }
    })
  )
}

async function openGraphOptions(): Promise<HTMLElement> {
  const header = await screen.findByRole('button', { name: /Additional graph options/ })
  await fireEvent.click(header)
  return header.parentElement!
}

describe('EmbeddedCustomGraphWidget', () => {
  test('places unit, range and visibility between axis and styling', async () => {
    renderWidget(null)
    const panel = within(await openGraphOptions())

    const rows = ['Axis', 'Unit', 'Explicit range', 'Metric visibility', 'Graph styling'].map(
      (label) => panel.getByText(label)
    )

    for (let index = 1; index < rows.length; index++) {
      expect(rows[index - 1]!.compareDocumentPosition(rows[index]!)).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING
      )
    }
  })

  test('previews the widget with its graph', async () => {
    renderWidget()

    await waitFor(() => expect(discoverBodies()).not.toHaveLength(0))
    expect(discoverBodies()[0]!.definition.data_sources).toEqual([
      expect.objectContaining({ id: 'A' })
    ])
  })

  test('previews a changed graph option', async () => {
    renderWidget()
    const panel = within(await openGraphOptions())

    await fireEvent.click(panel.getByRole('checkbox', { name: 'Show zero values' }))

    await waitFor(
      () => expect(discoverBodies().at(-1)?.definition.graph_options.omit_zero_metrics).toBe(true),
      { timeout: 2000 }
    )
  })
})
