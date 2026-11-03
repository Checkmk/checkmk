/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { Suspense, defineComponent, h, ref } from 'vue'

import CustomGraphEditor from '@/dashboard/components/Wizard/wizards/custom-graphs/editor/CustomGraphEditor.vue'
import type { CustomGraphOptions } from '@/graphing/designer/api'
import type { ApiDataSourceInput } from '@/graphing/designer/types'
import type { RequestedTimeRange } from '@/graphing/types'

import { filterDefinitions } from '../../../../../graphing/designer/fixtures'

vi.mock('@/graphing/api/burgerMenu', () => ({ loadMenu: vi.fn().mockResolvedValue([]) }))
vi.mock('@/graphing/api/graphPin', () => ({
  loadGraphPin: () => Promise.resolve(null),
  saveGraphPin: () => Promise.resolve()
}))
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: { inheritAttrs: false, template: '<div data-testid="time-series-graph" />' }
}))

const GRAPH_OPTIONS: CustomGraphOptions = {
  unit: { type: 'first_entry_with_unit' },
  explicit_vertical_range: { type: 'auto' },
  omit_zero_metrics: false
}

const LAST_FOUR_HOURS: RequestedTimeRange = { start: 1_700_000_000 - 4 * 3600, end: 1_700_000_000 }

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
} as ApiDataSourceInput

const DESIGNER_CONFIG = {
  palette: ['#28a2f3', '#ff8400'],
  warning_color: '#ffd000',
  critical_color: '#ff3232',
  telemetry_metrics_available: false,
  create_services_available: false,
  telemetry_metrics_default_title: '$METRIC_NAME$',
  title_macros: []
}

function fetchDataResponse(): unknown {
  return {
    data: {
      time_range: { start: 0, end: 3600, step: 60 },
      metrics: [],
      group_titles: [],
      horizontal_lines: [],
      warnings: [],
      errors: []
    },
    error: undefined,
    response: new Response(null, { status: 200 })
  }
}

function fetchDataBodies(postSpy: ReturnType<typeof vi.spyOn>): Record<string, unknown>[] {
  return postSpy.mock.calls
    .filter(([path]: unknown[]) => path === '/domain-types/custom_graph/actions/fetch_data/invoke')
    .map(([, options]: unknown[]) => (options as { body: Record<string, unknown> }).body)
}

let postSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  // Vue logs an "experimental feature" notice whenever <Suspense> renders, which fails the test.
  vi.spyOn(console, 'info').mockImplementation(() => {})
  vi.spyOn(client, 'GET').mockResolvedValue({
    data: DESIGNER_CONFIG,
    error: undefined,
    response: new Response(null, { status: 200 })
  } as never)
  postSpy = vi.spyOn(client, 'POST').mockResolvedValue(fetchDataResponse() as never)
})

function renderEditor(dataSources: ApiDataSourceInput[] = [RRD_SOURCE]) {
  const editor = ref<InstanceType<typeof CustomGraphEditor> | null>(null)
  const harness = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      // A Suspense at the root of the rendered tree never resolves under testing-library.
      return () =>
        h(
          'div',
          h(Suspense, null, {
            default: () =>
              h(CustomGraphEditor, {
                ref: editor,
                title: 'My graph',
                timeRange: LAST_FOUR_HOURS,
                dataSources,
                graphOptions: GRAPH_OPTIONS
              })
          })
        )
    }
  })
  render(harness)
  return { editor }
}

describe('CustomGraphEditor', () => {
  test("offers the designer's metrics and appearance tabs", async () => {
    renderEditor()

    expect(await screen.findByRole('tab', { name: 'Metrics selection' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Graph appearance' })).toBeInTheDocument()
  })

  test('previews the time range it is given', async () => {
    renderEditor()

    await waitFor(() => expect(fetchDataBodies(postSpy)).not.toHaveLength(0))
    expect(fetchDataBodies(postSpy)[0]!['requested_time_range']).toMatchObject(LAST_FOUR_HOURS)
  })

  test('previews the definition again once an added source is complete', async () => {
    renderEditor()
    await waitFor(() => expect(fetchDataBodies(postSpy)).toHaveLength(1))

    await fireEvent.click(await screen.findByRole('combobox', { name: 'Add source' }))
    await fireEvent.click(await screen.findByRole('option', { name: 'Constant line' }))
    await fireEvent.update(await screen.findByRole('spinbutton', { name: /^Constant at/ }), '5')

    await waitFor(() =>
      expect(
        (fetchDataBodies(postSpy).at(-1)!['content'] as { data_sources: unknown[] }).data_sources
      ).toHaveLength(2)
    )
  })

  test('submits the definition with its graph options', async () => {
    const { editor } = renderEditor()
    await screen.findByRole('tab', { name: 'Metrics selection' })

    const definition = editor.value!.submit()

    expect(definition).toEqual({
      data_sources: [expect.objectContaining({ id: 'A', metric_name: 'util' })],
      graph_options: GRAPH_OPTIONS
    })
  })

  test('submits nothing while a source has issues, and marks the metrics tab', async () => {
    const { editor } = renderEditor([])
    await fireEvent.click(await screen.findByRole('combobox', { name: 'Add source' }))
    await fireEvent.click(await screen.findByRole('option', { name: 'Checkmk RRD' }))

    const definition = editor.value!.submit()

    expect(definition).toBeNull()
    await waitFor(() =>
      expect(
        screen.getByRole('tab', { name: 'Metrics selection' }).querySelector('.cmk-icon')
      ).not.toBeNull()
    )
  })

  test('names the sources that keep it from submitting', async () => {
    const { editor } = renderEditor([])
    await fireEvent.click(await screen.findByRole('combobox', { name: 'Add source' }))
    await fireEvent.click(await screen.findByRole('option', { name: 'Checkmk RRD' }))

    editor.value!.submit()

    expect(
      await screen.findByText('Fix the issues with ID A before you continue.')
    ).toBeInTheDocument()
  })

  test('closes the calculation form to show the blocking sources', async () => {
    const { editor } = renderEditor([])
    await fireEvent.click(await screen.findByRole('combobox', { name: 'Add source' }))
    await fireEvent.click(await screen.findByRole('option', { name: 'Checkmk RRD' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Add calculation' }))
    // The inline form takes the place of the tabs.
    expect(screen.queryByRole('tab', { name: 'Metrics selection' })).not.toBeInTheDocument()

    editor.value!.submit()

    expect(await screen.findByRole('tab', { name: 'Metrics selection' })).toBeInTheDocument()
    expect(screen.getByText('Fix the issues with ID A before you continue.')).toBeInTheDocument()
  })

  test('shows why it cannot load instead of the designer', async () => {
    vi.spyOn(client, 'GET').mockRejectedValue(new Error('Designer config unavailable'))

    renderEditor()

    expect(await screen.findByText('Designer config unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Metrics selection' })).not.toBeInTheDocument()
  })
})
