/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { Response as SuggestionsResponse } from 'cmk-ui-library/components/CmkSuggestions'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import CustomGraphsWizard from '@/dashboard/components/Wizard/wizards/custom-graphs/CustomGraphsWizard.vue'
import { useProvideCustomGraphPermissions } from '@/dashboard/composables/useProvideCustomGraphPermissions'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

vi.mock('cmk-ui-library/components/FormAutocompleter/autocompleter', () => ({
  fetchSuggestions: vi.fn()
}))
vi.mock('@/graphing/api/burgerMenu', () => ({ loadMenu: vi.fn().mockResolvedValue([]) }))
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: { inheritAttrs: false, template: '<div data-testid="time-series-graph" />' }
}))

const CONSTANTS = {
  responsive_grid_breakpoints: {},
  widgets: { custom_graph: { filter_context: { restricted_to_single: [] } } }
} as unknown as DashboardConstants

const WIDGET_ATTRIBUTES_PATH = '/domain-types/dashboard/actions/compute-widget-attributes/invoke'
const WIDGET_TITLES_PATH = '/domain-types/dashboard/actions/compute-widget-titles/invoke'
const METADATA_PATH = '/domain-types/custom_graph_metadata/collections/all'

const LINKED_WIDGET = {
  content: {
    type: 'custom_graph',
    custom_graph: 'my_graph',
    timerange: 'dashboard',
    graph_render_options: {}
  },
  filter_context: { filters: {}, uses_infos: [] },
  general_settings: {
    title: { text: '$DEFAULT_TITLE$', render_mode: 'with_background' },
    render_background: true
  }
} as unknown as WidgetSpec

function ok(data: unknown): never {
  return { data, error: undefined, response: new Response(null, { status: 200 }) } as never
}

beforeEach(() => {
  // Suspense announces that it is experimental.
  vi.spyOn(console, 'info').mockImplementation(() => {})
  vi.mocked(fetchSuggestions).mockResolvedValue(
    new SuggestionsResponse([{ name: 'my_graph', title: 'My graph' }])
  )
  vi.spyOn(client, 'GET').mockImplementation(async (path: unknown) =>
    ok(
      path === METADATA_PATH
        ? { value: [{ id: 'my_graph', title: 'My graph', extensions: { owner: 'admin' } }] }
        : { value: [{ title: 'Last 4 hours', extensions: { total_seconds: 4 * 3600 } }] }
    )
  )
  vi.spyOn(client, 'POST').mockImplementation(async (path: unknown) =>
    ok(
      path === WIDGET_ATTRIBUTES_PATH
        ? { value: { filter_context: { uses_infos: [] } } }
        : path === WIDGET_TITLES_PATH
          ? { extensions: { titles: {} } }
          : { graphs: [] }
    )
  )
})

function renderWizard(editWidgetSpec: WidgetSpec | null, mayEditCustomGraph: boolean) {
  const onCloneGraph = vi.fn()
  const provider = defineComponent({
    setup() {
      useProvideDashboardConstants(CONSTANTS)
      useProvideCustomGraphPermissions({
        edit: mayEditCustomGraph,
        publish: { allUsers: false, contactGroups: false, sites: false }
      })
      useProvideMissingRuntimeFiltersAction(ref(true), () => {})
      return () =>
        h(
          'div',
          h(CustomGraphsWizard, {
            tick: 0,
            range: makeContentProps(null).range,
            dashboardKey: { name: 'main', owner: '' },
            contextFilters: {},
            editWidgetSpec,
            onCloneGraph
          })
        )
    }
  })
  render(provider)
  return { onCloneGraph }
}

describe('CustomGraphsWizard', () => {
  test('offers cloning the linked graph when editing', async () => {
    renderWizard(LINKED_WIDGET, true)

    expect(await screen.findByRole('button', { name: 'Clone & edit graph' })).toBeInTheDocument()
  })

  test('names the linked graph by its catalog title', async () => {
    renderWizard(LINKED_WIDGET, true)

    expect(
      await screen.findByRole('heading', { name: 'Linked to catalog graph “My graph”' })
    ).toBeInTheDocument()
  })

  test('offers no cloning to users who may not edit custom graphs', async () => {
    renderWizard(LINKED_WIDGET, false)

    await screen.findByRole('button', { name: 'Save widget' })
    expect(screen.queryByRole('button', { name: 'Clone & edit graph' })).not.toBeInTheDocument()
  })

  test('offers no cloning when adding a widget', async () => {
    renderWizard(null, true)

    await screen.findByRole('button', { name: 'Add & place widget' })
    expect(screen.queryByRole('button', { name: 'Clone & edit graph' })).not.toBeInTheDocument()
  })

  test('switches to cloning the linked graph', async () => {
    const { onCloneGraph } = renderWizard(LINKED_WIDGET, true)

    await fireEvent.click(await screen.findByRole('button', { name: 'Clone & edit graph' }))

    expect(onCloneGraph).toHaveBeenCalledWith('my_graph')
  })
})
