/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { configure, render, screen, within } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, toRaw } from 'vue'

import DashboardApp from '@/dashboard/DashboardApp.vue'
import {
  type DashboardConstants,
  DashboardFeatures,
  DashboardLayout,
  type DashboardMetadata
} from '@/dashboard/types/dashboard'
import type { DashboardPageProperties } from '@/dashboard/types/page'

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
const SOURCE_TEXT = 'Content of the anchored dashboard'
const REFUSAL = 'Dashboard ID already exists'

const constants: DashboardConstants = {
  responsive_grid_breakpoints: {
    XS: { min_width: 280, columns: 4 },
    S: { min_width: 535, columns: 8 },
    M: { min_width: 705, columns: 12 },
    L: { min_width: 961, columns: 12 },
    XL: { min_width: 1217, columns: 24 }
  },
  widgets: {
    static_text: {
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
  widgets: {
    note: {
      general_settings: {
        title: { text: 'Note', render_mode: 'with_background' },
        render_background: true
      },
      content: { type: 'static_text', text: SOURCE_TEXT },
      filter_context: { uses_infos: [], filters: {} },
      layout: { type: 'relative_grid', position: { x: 1, y: 1 }, size: { width: 30, height: 10 } }
    }
  }
}

const pageProperties: DashboardPageProperties = {
  initial_breadcrumb: [],
  dashboard: {
    metadata,
    filter_context: { context: {}, application_mode: 'overwrite', dropped_filters_warning: null }
  },
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
    edit_custom_graph: false
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

useMswServer(
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
      extensions: { titles: { note: 'Note' } }
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
  http.post(
    `${API}/domain-types/dashboard_responsive_grid/actions/clone_from_relative_grid/invoke`,
    () => HttpResponse.json({ title: 'Bad Request', status: 400, detail: REFUSAL }, { status: 400 })
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

async function migrateTheDashboard(): Promise<void> {
  const user = userEvent.setup()
  render(DashboardApp, { props: pageProperties })
  await screen.findByText(SOURCE_TEXT)

  await user.click(screen.getByRole('button', { name: 'Settings' }))
  await user.click(screen.getByText('Clone as responsive dashboard'))
  await user.click(await screen.findByRole('button', { name: 'Clone' }))
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
})
