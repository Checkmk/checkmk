/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { configure, fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, toRaw } from 'vue'

import DashboardApp from '@/dashboard/DashboardApp.vue'
import {
  type DashboardConstants,
  DashboardFeatures,
  DashboardLayout,
  type DashboardMetadata
} from '@/dashboard/types/dashboard'
import type { DashboardPageProperties } from '@/dashboard/types/page'
import type {
  ComputedMonitoringTable,
  ResponsiveGridWidgetLayout,
  ResponsiveGridWidgetLayouts
} from '@/dashboard/types/widget'
import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'

import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

// reka's dialog warns about the missing DialogTitle of the bare slide-in, which fails the test.
vi.mock('cmk-ui-library/components/CmkSlideIn', () => ({
  default: defineComponent({
    name: 'CmkSlideIn',
    props: {
      open: { type: Boolean, required: true },
      ariaLabel: { type: String, default: undefined }
    },
    setup(props, { slots }) {
      return () =>
        props.open
          ? h('div', { role: 'dialog', 'aria-label': props.ariaLabel }, slots.default?.())
          : null
    }
  })
}))

// Each test renders the whole app: the first render alone takes half a second here, and CI can be
// several times slower while other workers run alongside.
vi.setConfig({ testTimeout: 20_000 })
configure({ asyncUtilTimeout: 5_000 })

const API = `${location.protocol}//${location.host}/api/internal`
const OWNER = 'harry'
const SOURCE_ID = 'anchored_source'
const SOURCE_TITLE = 'Anchored dashboard to migrate'
const REFUSAL = 'Dashboard ID already exists'
const CLONE_ENDPOINT = `${API}/domain-types/dashboard_responsive_grid/actions/clone_from_relative_grid/invoke`

const widgetConstants: DashboardConstants['widgets'][string] = {
  filter_context: { restricted_to_single: [] },
  title_macros: [],
  layout: {
    relative: {
      initial_size: { width: 30, height: 10 },
      minimum_size: { width: 10, height: 5 },
      initial_position: { x: 1, y: 1 },
      is_resizable: true
    },
    responsive: {
      XS: { minimum_size: { columns: 4, rows: 4 }, initial_size: { columns: 4, rows: 7 } },
      S: { minimum_size: { columns: 4, rows: 4 }, initial_size: { columns: 4, rows: 7 } },
      M: { minimum_size: { columns: 4, rows: 4 }, initial_size: { columns: 6, rows: 7 } },
      L: { minimum_size: { columns: 3, rows: 4 }, initial_size: { columns: 4, rows: 7 } },
      XL: { minimum_size: { columns: 3, rows: 4 }, initial_size: { columns: 6, rows: 7 } }
    }
  }
}

const constants: DashboardConstants = {
  responsive_grid_breakpoints: {
    XS: { min_width: 280, columns: 4 },
    S: { min_width: 535, columns: 8 },
    M: { min_width: 705, columns: 12 },
    L: { min_width: 961, columns: 12 },
    XL: { min_width: 1217, columns: 24 }
  },
  widgets: {
    static_text: widgetConstants,
    monitoring_table: widgetConstants
  }
}

const metadata: DashboardMetadata = {
  name: SOURCE_ID,
  owner: OWNER,
  is_built_in: false,
  is_editable: true,
  layout_type: 'relative_grid',
  restricted_to_single: [],
  display: {
    title: SOURCE_TITLE,
    topic: { name: 'overview', breadcrumb: [] },
    hidden: false,
    sort_index: 99,
    hide_in_drop_down_menus: false
  }
}

const generalSettings = {
  title: { text: SOURCE_TITLE, render: true, include_context: false },
  description: '',
  menu: { topic: 'overview', sort_index: 99, search_terms: [], is_show_more: false },
  visibility: { hide_in_monitor_menu: false, hide_in_drop_down_menus: false, share: 'no' }
}

function staticTextWidget(
  title: string,
  position: { x: number; y: number },
  size: { width: number; height: number }
) {
  return {
    general_settings: {
      title: { text: title, render_mode: 'with_background' },
      render_background: true
    },
    content: { type: 'static_text', text: `Content of ${title}` },
    filter_context: { uses_infos: [], filters: {} },
    layout: { type: 'relative_grid', position, size }
  }
}

// Relative grid units are 10 px raster cells: two widgets side by side above one as wide as both.
const sourceWidgets = {
  top_left: staticTextWidget('Top left', { x: 1, y: 1 }, { width: 40, height: 30 }),
  top_right: staticTextWidget('Top right', { x: 41, y: 1 }, { width: 40, height: 30 }),
  bottom: staticTextWidget('Bottom', { x: 1, y: 31 }, { width: 80, height: 30 })
}
const SOURCE_TEXT = sourceWidgets.bottom.content.text

const sourceDashboard = {
  owner: OWNER,
  last_modified_at: '2026-10-01T00:00:00Z',
  is_built_in: false,
  public_token: null,
  general_settings: generalSettings,
  filter_context: {
    restricted_to_single: [],
    filters: {},
    mandatory_context_filters: []
  },
  layout: { type: 'relative_grid' },
  widgets: sourceWidgets
}

const TABLE_WIDGET_ID = 'hosts'

const hostsTableWidget = {
  general_settings: {
    title: { text: 'Hosts', render_mode: 'with_background' },
    render_background: true
  },
  content: {
    type: 'monitoring_table',
    table: 'hosts',
    columns: ['state', 'name'],
    sort: ['name:asc'],
    limit: 100,
    date_format: '%Y-%m-%d',
    timestamp_format: 'mixed'
  },
  filter_context: { uses_infos: [], filters: {} }
}

const BREAKPOINTS = ['XS', 'S', 'M', 'L', 'XL'] as const

// The same hosts table, once on each grid a dashboard can arrange its widgets on.
const hostsTableDashboards = {
  relative_grid: {
    ...sourceDashboard,
    widgets: {
      [TABLE_WIDGET_ID]: {
        ...hostsTableWidget,
        layout: { type: 'relative_grid', position: { x: 1, y: 1 }, size: { width: 80, height: 40 } }
      }
    }
  },
  responsive_grid: {
    ...sourceDashboard,
    layout: {
      type: 'responsive_grid',
      layouts: { default: { title: 'Default', breakpoints: BREAKPOINTS } }
    },
    widgets: {
      [TABLE_WIDGET_ID]: {
        ...hostsTableWidget,
        layout: {
          type: 'responsive_grid',
          layouts: {
            default: Object.fromEntries(
              BREAKPOINTS.map((bp) => [
                bp,
                { position: { x: 0, y: 0 }, size: { columns: 4, rows: 7 } }
              ])
            )
          }
        }
      }
    }
  }
}

const hostsTable: ComputedMonitoringTable = {
  table: 'hosts',
  rows: [
    {
      name: 'heute',
      state: 'UP',
      is_flapping: false,
      stale: false,
      site_id: 'heute',
      legacy_host_status_link: 'view.py?view_name=hoststatus&host=heute&site=heute',
      setup_access: true
    }
  ],
  matched: 1,
  total: 1,
  unapplied_filters: [],
  unreachable_sites: [],
  actions: [{ ident: 'reschedule', title: 'Reschedule', icon: 'reload' }],
  links: [],
  host_actions: [],
  host_links: []
}

const pageFilterContext = {
  context: {},
  application_mode: 'overwrite',
  dropped_filters_warning: null
} as const

const pageProperties: DashboardPageProperties = {
  initial_breadcrumb: [],
  dashboard: { metadata, filter_context: pageFilterContext },
  mode: 'display',
  url_params: {},
  links: { list_dashboards: '', user_guide: '' },
  available_layouts: [DashboardLayout.RELATIVE_GRID, DashboardLayout.RESPONSIVE_GRID],
  available_features: { dashboard_features: DashboardFeatures.UNRESTRICTED, ntop_active: false },
  permissions: {
    publish_to_all: false,
    publish_to_contact_groups: false,
    publish_to_foreign_contact_groups: false,
    publish_to_sites: false,
    edit_custom_graph: false,
    publish_custom_graph_to_all: false,
    publish_custom_graph_to_contact_groups: false,
    publish_custom_graph_to_foreign_contact_groups: false,
    publish_custom_graph_to_sites: false
  },
  logged_in_user: OWNER,
  global_time_picker: {
    custom_time_ranges: [],
    default_time_range: 4 * 3600,
    server_time_zone: 'UTC',
    first_day_of_week: null,
    refresh: {
      interval_seconds: null,
      interval_choices_seconds: [],
      starts_live: false,
      reloads_page_content: false
    }
  },
  drill_up: null
}

function emptyCollection(domainType: string) {
  return HttpResponse.json({ domainType, id: 'all', links: [], value: [] })
}

function refusal() {
  return HttpResponse.json({ title: 'Bad Request', status: 400, detail: REFUSAL }, { status: 400 })
}

const server = useMswServer(
  http.get(`${API}/domain-types/visual_filter/collections/all`, () =>
    emptyCollection('visual_filter')
  ),
  http.get(`${API}/domain-types/visual_filter_group/collections/all`, () =>
    emptyCollection('visual_filter_group')
  ),
  http.get(`${API}/objects/constant/visual_info/collections/all`, () =>
    emptyCollection('constant')
  ),
  http.get(`${API}/domain-types/icon/collections/all`, () => emptyCollection('icon')),
  http.get(`${API}/domain-types/icon_category/collections/all`, () =>
    emptyCollection('icon_category')
  ),
  http.get(`${API}/domain-types/icon_emblem/collections/all`, () => emptyCollection('icon_emblem')),
  http.get(`${API}/domain-types/pagetype_topic/collections/all`, () =>
    HttpResponse.json({
      domainType: 'pagetype_topic',
      id: 'all',
      links: [],
      value: [
        {
          domainType: 'pagetype_topic',
          id: 'overview',
          title: 'Overview',
          links: [],
          extensions: { sort_index: 1, is_default: true }
        }
      ]
    })
  ),
  http.post(`${API}/domain-types/dashboard/actions/compute-widget-titles/invoke`, () =>
    HttpResponse.json({
      domainType: 'dashboard',
      id: 'titles',
      links: [],
      extensions: {
        titles: Object.fromEntries(
          Object.entries(sourceWidgets).map(([widgetId, widget]) => [
            widgetId,
            widget.general_settings.title.text
          ])
        )
      }
    })
  ),
  http.get(`${API}/objects/constant/dashboard`, () =>
    HttpResponse.json({ domainType: 'constant', id: 'dashboard', links: [], extensions: constants })
  ),
  http.get(`${API}/objects/dashboard_metadata/${SOURCE_ID}`, () =>
    HttpResponse.json({
      domainType: 'dashboard_metadata',
      id: SOURCE_ID,
      links: [],
      extensions: metadata
    })
  ),
  http.get(`${API}/domain-types/dashboard_metadata/collections/all`, () =>
    HttpResponse.json({
      domainType: 'dashboard_metadata',
      id: 'all',
      links: [],
      value: [{ domainType: 'dashboard_metadata', id: SOURCE_ID, links: [], extensions: metadata }]
    })
  ),
  http.get(`${API}/objects/dashboard_relative_grid/${SOURCE_ID}`, () =>
    HttpResponse.json({
      domainType: 'dashboard_relative_grid',
      id: SOURCE_ID,
      links: [],
      extensions: sourceDashboard
    })
  ),
  http.post(CLONE_ENDPOINT, refusal)
)

// The page loads core-js, whose structuredClone copies the reactive proxies the app clones;
// the native one of the test runtime refuses them.
const nativeStructuredClone = globalThis.structuredClone
beforeEach(() => {
  vi.stubGlobal('structuredClone', (value: unknown) => nativeStructuredClone(toRaw(value)))
  // Vue logs an "experimental feature" notice whenever <Suspense> renders, which fails the test.
  vi.spyOn(console, 'info').mockImplementation(() => {})
})

function captureMigrationRequests(): {
  widget_layouts: Record<string, ResponsiveGridWidgetLayouts>
}[] {
  const sentBodies: { widget_layouts: Record<string, ResponsiveGridWidgetLayouts> }[] = []
  server.use(
    http.post(CLONE_ENDPOINT, async ({ request }) => {
      sentBodies.push(
        (await request.json()) as { widget_layouts: Record<string, ResponsiveGridWidgetLayouts> }
      )
      // Accepting the clone would navigate to the copy, which jsdom cannot do.
      return refusal()
    })
  )
  return sentBodies
}

function placementAtWidestBreakpoint(
  layouts: ResponsiveGridWidgetLayouts
): ResponsiveGridWidgetLayout {
  return layouts.layouts['default']!['XL']!
}

function endColumnOf(placement: ResponsiveGridWidgetLayout): number {
  return placement.position.x + placement.size.columns
}

function endRowOf(placement: ResponsiveGridWidgetLayout): number {
  return placement.position.y + placement.size.rows
}

async function migrateTheDashboard(): Promise<void> {
  const user = userEvent.setup()
  render(DashboardApp, { props: pageProperties })
  await screen.findByText(SOURCE_TEXT)

  await user.click(screen.getByRole('button', { name: 'Settings' }))
  await user.click(screen.getByText('Clone as responsive dashboard'))
  await user.click(await screen.findByRole('button', { name: 'Clone' }))
}

type Grid = keyof typeof hostsTableDashboards

/** Shows a dashboard of a hosts table on the grid instead, whose host cannot be rescheduled. */
function showHostsTableFailingToReschedule(grid: Grid): DashboardPageProperties {
  const gridMetadata = { ...metadata, layout_type: grid }
  server.use(
    http.get(`${API}/objects/dashboard_metadata/${SOURCE_ID}`, () =>
      HttpResponse.json({
        domainType: 'dashboard_metadata',
        id: SOURCE_ID,
        links: [],
        extensions: gridMetadata
      })
    ),
    http.get(`${API}/objects/dashboard_${grid}/${SOURCE_ID}`, () =>
      HttpResponse.json({
        domainType: `dashboard_${grid}`,
        id: SOURCE_ID,
        links: [],
        extensions: hostsTableDashboards[grid]
      })
    ),
    http.post(`${API}/domain-types/dashboard/actions/compute-widget-titles/invoke`, () =>
      HttpResponse.json({
        domainType: 'dashboard',
        id: 'titles',
        links: [],
        extensions: { titles: { [TABLE_WIDGET_ID]: 'Hosts' } }
      })
    ),
    http.post(`${API}/domain-types/dashboard/actions/compute-monitoring-table/invoke`, () =>
      HttpResponse.json({ domainType: 'widget-compute', value: hostsTable })
    ),
    restApiHttp.get('/monitor/hosts/{hostname}/action_menu', ({ response }) =>
      response(200).json({ items: [] })
    ),
    restApiHttp.post('/monitor/hosts/actions/reschedule', ({ response }) =>
      response.untyped(HttpResponse.json({ title: 'Internal error' }, { status: 500 }))
    )
  )
  return {
    ...pageProperties,
    dashboard: { metadata: gridMetadata, filter_context: pageFilterContext }
  }
}

/** jsdom does no layout: the table shows its rows only once it is told it has room for them. */
async function renderHostsTable(props: DashboardPageProperties): Promise<void> {
  FakeResizeObserver.instances = []
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
  vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(600)
  render(DashboardApp, { props })
  await waitFor(() => {
    deliverSize(800, 400)
    expect(screen.getByText('heute')).toBeInTheDocument()
  })
}

describe('DashboardApp', () => {
  it('tells why the migration of the dashboard failed', async () => {
    await migrateTheDashboard()

    const failure = await screen.findByRole('alert')
    expect(within(failure).getByText('Dashboard not cloned')).toBeInTheDocument()
    expect(within(failure).getByText(`Bad Request: ${REFUSAL}`)).toBeInTheDocument()
  })

  it('keeps the anchored dashboard open when its migration fails', async () => {
    await migrateTheDashboard()

    await screen.findByRole('alert')
    expect(screen.getByText(SOURCE_TEXT)).toBeInTheDocument()
  })

  it('sends the measured arrangement of the widgets with the migration', async () => {
    const sentBodies = captureMigrationRequests()

    await migrateTheDashboard()

    await screen.findByRole('alert')
    const [{ widget_layouts: widgetLayouts }] = sentBodies as [(typeof sentBodies)[number]]
    const topLeft = placementAtWidestBreakpoint(widgetLayouts['top_left']!)
    const topRight = placementAtWidestBreakpoint(widgetLayouts['top_right']!)
    const bottom = placementAtWidestBreakpoint(widgetLayouts['bottom']!)
    expect(topRight.position).toEqual({ x: endColumnOf(topLeft), y: topLeft.position.y })
    expect(bottom.position).toEqual({ x: topLeft.position.x, y: endRowOf(topLeft) })
    expect(endColumnOf(bottom)).toBe(endColumnOf(topRight))
  })

  it.each<Grid>(['relative_grid', 'responsive_grid'])(
    'tells in its alert box that an action run in a widget on the %s failed',
    async (grid) => {
      const props = showHostsTableFailingToReschedule(grid)
      const user = userEvent.setup()
      await renderHostsTable(props)

      await user.click(screen.getByRole('button', { name: 'More actions' }))
      await user.click(await screen.findByRole('menuitem', { name: 'Reschedule' }))

      const failure = await screen.findByRole('alert')
      expect(failure).toHaveTextContent('Could not reschedule the checks for the selected hosts')
    }
  )
})

describe('DashboardApp on a switch to another dashboard', () => {
  const pageUrl = window.location.href
  const OTHER_ID = 'other_dashboard'
  const OTHER_TITLE = 'Other dashboard'
  const otherMetadata: DashboardMetadata = {
    ...metadata,
    name: OTHER_ID,
    display: { ...metadata.display, title: OTHER_TITLE }
  }

  afterEach(() => {
    resetGlobalTimeState()
    window.history.replaceState({}, '', pageUrl)
  })

  function serveTheOtherDashboard(): void {
    server.use(
      http.get(`${API}/domain-types/dashboard_metadata/collections/all`, () =>
        HttpResponse.json({
          domainType: 'dashboard_metadata',
          id: 'all',
          links: [],
          value: [metadata, otherMetadata].map((extensions) => ({
            domainType: 'dashboard_metadata',
            id: extensions.name,
            links: [],
            extensions
          }))
        })
      ),
      http.get(`${API}/objects/dashboard_metadata/${OTHER_ID}`, () =>
        HttpResponse.json({
          domainType: 'dashboard_metadata',
          id: OTHER_ID,
          links: [],
          extensions: otherMetadata
        })
      ),
      http.get(`${API}/objects/dashboard_relative_grid/${OTHER_ID}`, () =>
        HttpResponse.json({
          domainType: 'dashboard_relative_grid',
          id: OTHER_ID,
          links: [],
          extensions: sourceDashboard
        })
      )
    )
  }

  it('keeps the time range in the address bar', async () => {
    serveTheOtherDashboard()
    render(DashboardApp, { props: pageProperties })
    await screen.findByText(SOURCE_TEXT)
    const [start, end] = [Date.parse('2026-01-01T00:00:00Z'), Date.parse('2026-01-01T04:00:00Z')]
    useGlobalTimeRange().setActiveTimeRange(
      { from: fromDate(new Date(start), 'UTC'), to: fromDate(new Date(end), 'UTC') },
      'time_picker'
    )
    useGlobalRefresh().pauseRefresh()

    await fireEvent.focus(screen.getByPlaceholderText(SOURCE_TITLE))
    await fireEvent.click(await screen.findByText(OTHER_TITLE))

    await waitFor(() => {
      expect(Object.fromEntries(new URL(window.location.href).searchParams)).toMatchObject({
        name: OTHER_ID,
        from: String(start),
        to: String(end)
      })
    })
  })
})
