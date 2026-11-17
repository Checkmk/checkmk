/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import userEvent from '@testing-library/user-event'
import { configure, fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, toRaw } from 'vue'

import DashboardApp from '@/dashboard/DashboardApp.vue'
import {
  type DashboardConstants,
  DashboardFeatures,
  DashboardLayout,
  type DashboardMetadata,
  type RelativeGridDashboardResponse,
  type ResponsiveGridDashboardResponse
} from '@/dashboard/types/dashboard'
import type { DashboardPageProperties } from '@/dashboard/types/page'
import type {
  AlertOverview,
  ComputedMonitoringTable,
  RelativeGridWidget,
  ResponsiveGridWidgetLayout,
  ResponsiveGridWidgetLayouts,
  WidgetTimeRange
} from '@/dashboard/types/widget'
import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { durationSeconds, endsNow } from '@/graphing/GlobalTimePicker/private/timeRange'

import { dashboardMetadataHandlers, mainMenuTopicsHandler } from '@tests/dashboard/apiHandlers'
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

const OWNER = 'harry'
const SOURCE_ID = 'anchored_source'
const SOURCE_TITLE = 'Anchored dashboard to migrate'
const REFUSAL = 'Dashboard ID already exists'

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
    monitoring_table: widgetConstants,
    alert_overview: widgetConstants,
    url: widgetConstants
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
} satisfies RelativeGridDashboardResponse['general_settings']

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
  } satisfies RelativeGridWidget
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
    uses_infos: [],
    filters: {},
    mandatory_context_filters: []
  },
  layout: { type: 'relative_grid' },
  widgets: sourceWidgets
} satisfies RelativeGridDashboardResponse

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
    timestamp_format: 'mixed',
    read_only: false
  },
  filter_context: { uses_infos: [], filters: {} }
} satisfies Omit<RelativeGridWidget, 'layout'>

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
  } satisfies RelativeGridDashboardResponse,
  responsive_grid: {
    ...sourceDashboard,
    layout: {
      type: 'responsive_grid',
      layouts: { default: { title: 'Default', breakpoints: [...BREAKPOINTS] } }
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
  } satisfies ResponsiveGridDashboardResponse
}

// An alert overview over the dashboard's window, the whole dashboard wide.
const alertOverviewDashboard = {
  ...sourceDashboard,
  widgets: {
    alerts: {
      general_settings: {
        title: { text: 'Alerts', render_mode: 'with_background' },
        render_background: true
      },
      content: { type: 'alert_overview', time_range: 'dashboard' },
      filter_context: { uses_infos: [], filters: {} },
      layout: { type: 'relative_grid', position: { x: 1, y: 1 }, size: { width: 80, height: 40 } }
    }
  }
} satisfies RelativeGridDashboardResponse

const alertOverview: AlertOverview = {
  elements: [
    {
      site_id: 'heute',
      host_name: 'heute',
      service_description: 'CPU load',
      num_ok: 1,
      num_warn: 1,
      num_crit: 1,
      num_unknown: 0,
      num_problems: 2,
      links: [],
      link_properties: { links: [] }
    }
  ]
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
  shareable_contact_groups: [],
  shareable_sites: [],
  shareable_custom_graph_contact_groups: [],
  shareable_custom_graph_sites: [],
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

const refusal = { title: 'Bad Request', status: 400, detail: REFUSAL }

function emptyCollection<DomainType extends string>(domainType: DomainType) {
  return { domainType, id: 'all', links: [], value: [] }
}

const server = useMswServer(
  restApiHttp.get('/domain-types/visual_filter/collections/all', ({ response }) =>
    response(200).json(emptyCollection('visual_filter'))
  ),
  restApiHttp.get('/domain-types/visual_filter_group/collections/all', ({ response }) =>
    response(200).json(emptyCollection('visual_filter_group'))
  ),
  restApiHttp.get('/objects/constant/visual_info/collections/all', ({ response }) =>
    response(200).json(emptyCollection('constant'))
  ),
  restApiHttp.get('/domain-types/icon/collections/all', ({ response }) =>
    response(200).json(emptyCollection('icon'))
  ),
  restApiHttp.get('/domain-types/icon_category/collections/all', ({ response }) =>
    response(200).json(emptyCollection('icon_category'))
  ),
  restApiHttp.get('/domain-types/icon_emblem/collections/all', ({ response }) =>
    response(200).json(emptyCollection('icon_emblem'))
  ),
  mainMenuTopicsHandler([{ id: 'overview', title: 'Overview', sortIndex: 1, isDefault: true }]),
  restApiHttp.post('/domain-types/dashboard/actions/compute-widget-titles/invoke', ({ response }) =>
    response(200).json({
      domainType: 'dashboard-widget-titles',
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
  restApiHttp.get('/objects/constant/dashboard', ({ response }) =>
    response(200).json({
      domainType: 'constant',
      id: 'dashboard',
      title: 'Dashboard',
      links: [],
      extensions: constants
    })
  ),
  ...dashboardMetadataHandlers([metadata]),
  restApiHttp.get('/objects/dashboard_relative_grid/{dashboard_id}', ({ params, response }) =>
    response(200).json({
      domainType: 'dashboard',
      id: params.dashboard_id,
      title: SOURCE_TITLE,
      links: [],
      extensions: sourceDashboard
    })
  ),
  restApiHttp.post(
    '/domain-types/dashboard_responsive_grid/actions/clone_from_relative_grid/invoke',
    ({ response }) => response(400).json(refusal)
  )
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
    restApiHttp.post(
      '/domain-types/dashboard_responsive_grid/actions/clone_from_relative_grid/invoke',
      async ({ request, response }) => {
        sentBodies.push(await request.json())
        // Accepting the clone would navigate to the copy, which jsdom cannot do.
        return response(400).json(refusal)
      }
    )
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
    ...dashboardMetadataHandlers([gridMetadata]),
    restApiHttp.get('/objects/dashboard_relative_grid/{dashboard_id}', ({ response }) =>
      response(200).json({
        domainType: 'dashboard',
        id: SOURCE_ID,
        title: SOURCE_TITLE,
        links: [],
        extensions: hostsTableDashboards.relative_grid
      })
    ),
    restApiHttp.get('/objects/dashboard_responsive_grid/{dashboard_id}', ({ response }) =>
      response(200).json({
        domainType: 'dashboard',
        id: SOURCE_ID,
        title: SOURCE_TITLE,
        links: [],
        extensions: hostsTableDashboards.responsive_grid
      })
    ),
    restApiHttp.post(
      '/domain-types/dashboard/actions/compute-widget-titles/invoke',
      ({ response }) =>
        response(200).json({
          domainType: 'dashboard-widget-titles',
          id: 'titles',
          links: [],
          extensions: { titles: { [TABLE_WIDGET_ID]: 'Hosts' } }
        })
    ),
    restApiHttp.post(
      '/domain-types/dashboard/actions/compute-monitoring-table/invoke',
      ({ response }) => response(200).json({ domainType: 'widget-compute', value: hostsTable })
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

const EMBEDDED_PAGE_TITLE = 'Custom page'

/** Shows a dashboard with these filters and one widget that embeds a page with them. */
function showEmbeddedPageWithDashboardFilters(filters: Record<string, Record<string, string>>) {
  server.use(
    restApiHttp.post(
      '/domain-types/dashboard/actions/compute-widget-titles/invoke',
      ({ response }) =>
        response(200).json({
          domainType: 'dashboard-widget-titles',
          id: 'titles',
          links: [],
          extensions: { titles: { embedded_page: EMBEDDED_PAGE_TITLE } }
        })
    ),
    restApiHttp.get('/objects/dashboard_relative_grid/{dashboard_id}', ({ response }) =>
      response(200).json({
        domainType: 'dashboard',
        id: SOURCE_ID,
        title: SOURCE_TITLE,
        links: [],
        extensions: {
          ...sourceDashboard,
          filter_context: { ...sourceDashboard.filter_context, filters },
          widgets: {
            embedded_page: {
              general_settings: {
                title: { text: EMBEDDED_PAGE_TITLE, render_mode: 'with_background' },
                render_background: true
              },
              content: {
                type: 'url',
                url: 'custom_page.py',
                include_context: true,
                include_time_range: false
              },
              filter_context: { uses_infos: [], filters: {} },
              layout: {
                type: 'relative_grid',
                position: { x: 1, y: 1 },
                size: { width: 80, height: 40 }
              }
            }
          }
        }
      })
    )
  )
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

  it('passes the dashboard filters to an embedded page that includes them', async () => {
    showEmbeddedPageWithDashboardFilters({ host: { host: 'heute' } })

    render(DashboardApp, { props: pageProperties })

    const frame = await screen.findByTitle(EMBEDDED_PAGE_TITLE)
    const source = new URL(frame.getAttribute('src')!, location.href)
    expect(source.searchParams.get('host')).toBe('heute')
  })

  it('names each widget by its title', async () => {
    render(DashboardApp, { props: pageProperties })

    const widget = await screen.findByRole('group', { name: 'Bottom' })
    expect(widget).toHaveTextContent(SOURCE_TEXT)
  })
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
    server.use(...dashboardMetadataHandlers([metadata, otherMetadata]))
  }

  it('takes the alerts of the actions run in its widgets away', async () => {
    const props = showHostsTableFailingToReschedule('relative_grid')
    serveTheOtherDashboard()
    const user = userEvent.setup()
    await renderHostsTable(props)
    await user.click(screen.getByRole('button', { name: 'More actions' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Reschedule' }))
    await screen.findByText('Could not reschedule the checks for the selected hosts')

    await fireEvent.focus(screen.getByPlaceholderText(SOURCE_TITLE))
    await fireEvent.click(await screen.findByText(OTHER_TITLE))

    await waitFor(() => {
      expect(new URL(window.location.href).searchParams.get('name')).toBe(OTHER_ID)
    })
    await waitFor(() => {
      deliverSize(800, 400)
      expect(screen.getByText('heute')).toBeInTheDocument()
    })
    expect(
      screen.queryByText('Could not reschedule the checks for the selected hosts')
    ).not.toBeInTheDocument()
  })

  /** Both dashboards show an alert overview; returns the windows that the overviews fetch for. */
  function serveAlertOverviewsOnBoth(): WidgetTimeRange[] {
    const fetchedWindows: WidgetTimeRange[] = []
    serveTheOtherDashboard()
    server.use(
      restApiHttp.get('/objects/dashboard_relative_grid/{dashboard_id}', ({ params, response }) =>
        response(200).json({
          domainType: 'dashboard',
          id: params.dashboard_id,
          title: SOURCE_TITLE,
          links: [],
          extensions: alertOverviewDashboard
        })
      ),
      restApiHttp.post(
        '/domain-types/dashboard/actions/compute-alert-overview/invoke',
        async ({ request, response }) => {
          fetchedWindows.push((await request.json()).time_range)
          return response(200).json({ domainType: 'widget-compute', value: alertOverview })
        }
      )
    )
    return fetchedWindows
  }

  it('fetches the other dashboard once, for the default window', async () => {
    const fetchedWindows = serveAlertOverviewsOnBoth()
    FakeResizeObserver.instances = []
    vi.stubGlobal('ResizeObserver', FakeResizeObserver)
    render(DashboardApp, { props: pageProperties })
    await screen.findByPlaceholderText(SOURCE_TITLE)
    const [start, end] = [Date.parse('2026-01-01T00:00:00Z'), Date.parse('2026-01-01T01:00:00Z')]
    useGlobalTimeRange().setActiveTimeRange(
      { from: fromDate(new Date(start), 'UTC'), to: fromDate(new Date(end), 'UTC') },
      'time_picker'
    )
    await waitFor(() => {
      expect(fetchedWindows.map((window) => Date.parse(window.start))).toContain(start)
    })
    fetchedWindows.length = 0

    await fireEvent.focus(screen.getByPlaceholderText(SOURCE_TITLE))
    await fireEvent.click(await screen.findByText(OTHER_TITLE))
    await waitFor(() => {
      expect(new URL(window.location.href).searchParams.get('name')).toBe(OTHER_ID)
    })
    await waitFor(() => {
      deliverSize(800, 400)
      expect(screen.getByRole('figure', { name: '1 object with alerts' })).toBeInTheDocument()
    })

    expect(
      fetchedWindows.map((window) => (Date.parse(window.end) - Date.parse(window.start)) / 1000)
    ).toEqual([pageProperties.global_time_picker.default_time_range])
  })

  it('starts the other dashboard the way a link to it starts', async () => {
    serveTheOtherDashboard()
    render(DashboardApp, { props: pageProperties })
    await screen.findByText(SOURCE_TEXT)
    const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()
    const { refreshIntervalSeconds, refreshPaused, pauseRefresh, setRefreshIntervalSeconds } =
      useGlobalRefresh()
    const defaultInterval = refreshIntervalSeconds.value
    const [start, end] = [Date.parse('2026-01-01T00:00:00Z'), Date.parse('2026-01-01T04:00:00Z')]
    setActiveTimeRange(
      { from: fromDate(new Date(start), 'UTC'), to: fromDate(new Date(end), 'UTC') },
      'time_picker'
    )
    pauseRefresh()
    setRefreshIntervalSeconds(2 * defaultInterval)

    await fireEvent.focus(screen.getByPlaceholderText(SOURCE_TITLE))
    await fireEvent.click(await screen.findByText(OTHER_TITLE))

    await waitFor(() => {
      expect(new URL(window.location.href).searchParams.get('name')).toBe(OTHER_ID)
    })
    expect(Object.fromEntries(new URL(window.location.href).searchParams)).toEqual({
      name: OTHER_ID,
      owner: OWNER
    })
    expect(durationSeconds(activeTimeRange.value!)).toBe(
      pageProperties.global_time_picker.default_time_range
    )
    expect(endsNow(activeTimeRange.value!)).toBe(true)
    expect(refreshPaused.value).toBe(false)
    expect(refreshIntervalSeconds.value).toBe(defaultInterval)
  })
})
