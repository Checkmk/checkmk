/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import type {
  UseWidgetHandler,
  WidgetContentType,
  WidgetProps
} from '@/dashboard/components/Wizard/types'
import { useHostState } from '@/dashboard/components/Wizard/wizards/hosts-site/stage2/HostState/composables/useHostState'
import { useHostStatistics } from '@/dashboard/components/Wizard/wizards/hosts-site/stage2/HostStatistics/composables/useHostStatistics'
import { useSiteOverview } from '@/dashboard/components/Wizard/wizards/hosts-site/stage2/SiteOverview/composables/useSiteOverview'
import { useInventory } from '@/dashboard/components/Wizard/wizards/hw_sw_inventory/stage2/InventoryWidget/useInventory'
import { useServiceState } from '@/dashboard/components/Wizard/wizards/services/stage2/ServiceState/composables/useServiceState'
import { useServiceStatistics } from '@/dashboard/components/Wizard/wizards/services/stage2/ServiceStatistics/composables/useServiceStatistics'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

// Every link these tests store is one every widget takes.
type ContextualLinkSpec =
  | components['schemas']['ContextualLinkNone']
  | components['schemas']['ContextualLinkDefault']
  | components['schemas']['ContextualLinkInherited']

interface LinkWizard {
  name: string
  type: string
  openWizard: (stored: WidgetContentType | null) => Promise<UseWidgetHandler>
  storedContent: (contextualLink: ContextualLinkSpec) => WidgetContentType
}

const WIZARDS: LinkWizard[] = [
  {
    name: 'useHostStatistics',
    type: 'host_stats',
    openWizard: (stored) => useHostStatistics({}, stored && storedSpec(stored)),
    storedContent: (link) => ({ type: 'host_stats', contextual_link: link })
  },
  {
    name: 'useServiceStatistics',
    type: 'service_stats',
    openWizard: (stored) => useServiceStatistics({}, stored && storedSpec(stored)),
    storedContent: (link) => ({ type: 'service_stats', contextual_link: link })
  },
  {
    name: 'useHostState',
    type: 'host_state',
    openWizard: (stored) => useHostState({}, stored && storedSpec(stored)),
    storedContent: (link) => ({ type: 'host_state', contextual_link: link })
  },
  {
    name: 'useServiceState',
    type: 'service_state',
    openWizard: (stored) => useServiceState({}, stored && storedSpec(stored)),
    storedContent: (link) => ({ type: 'service_state', contextual_link: link })
  },
  {
    name: 'useInventory',
    type: 'inventory',
    openWizard: (stored) =>
      useInventory(ref('.hardware.cpu.cores'), {}, stored && storedProps(stored)),
    storedContent: (link) => ({
      type: 'inventory',
      path: '.hardware.cpu.cores',
      contextual_link: link
    })
  },
  {
    name: 'useSiteOverview',
    type: 'site_overview',
    openWizard: (stored) => useSiteOverview({}, stored && storedSpec(stored)),
    storedContent: (link) => ({
      type: 'site_overview',
      dataset: 'hosts',
      hexagon_size: 'large',
      contextual_link: link
    })
  }
]

const GENERAL_SETTINGS: WidgetSpec['general_settings'] = {
  title: { text: 'Widget', render_mode: 'with_background' },
  render_background: true
}

function storedSpec(content: WidgetContentType): WidgetSpec {
  return {
    content,
    filter_context: { filters: {}, uses_infos: [] },
    general_settings: GENERAL_SETTINGS
  }
}

function storedProps(content: WidgetContentType): WidgetProps {
  return {
    content,
    effectiveTitle: 'Widget',
    effective_filter_context: { filters: {}, uses_infos: [], restricted_to_single: [] },
    general_settings: GENERAL_SETTINGS
  }
}

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const server = setupServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Widget' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: [] } } })
  )
)

const WIDGET_CONSTANTS: DashboardConstants['widgets'][string] = {
  filter_context: { restricted_to_single: [] },
  layout: {
    relative: {
      initial_position: { x: 1, y: 1 },
      initial_size: { width: 10, height: 10 },
      is_resizable: true,
      minimum_size: { width: 1, height: 1 }
    },
    responsive: {}
  },
  title_macros: []
}

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: Object.fromEntries(WIZARDS.map(({ type }) => [type, WIDGET_CONSTANTS]))
}

async function open(openWizard: LinkWizard['openWizard'], stored: WidgetContentType | null = null) {
  let handler: Promise<UseWidgetHandler> | undefined
  const consumer = defineComponent({
    setup() {
      handler = openWizard(stored)
      return () => h('div')
    }
  })
  render(
    defineComponent({
      setup() {
        useProvideDashboardConstants(CONSTANTS)
        return () => h(consumer)
      }
    })
  )
  return handler!
}

const INHERITED: ContextualLinkSpec = {
  type: 'inherited',
  location: { type: 'views', name: 'allhosts', owner: null },
  include_context: false,
  include_time_range: false,
  show_filter_form: false
}

async function submittedLink(handler: UseWidgetHandler): Promise<unknown> {
  const { content } = await handler.getSubmitProps()
  return 'contextual_link' in content ? content.contextual_link : undefined
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe.each(WIZARDS)('$name', ({ openWizard, storedContent }) => {
  it('submits the default link for a new widget, so the widget takes its built-in link', async () => {
    const handler = await open(openWizard)

    expect(await submittedLink(handler)).toEqual({ type: 'default' })
  })

  it('keeps a stored inherited link when it edits a widget', async () => {
    const handler = await open(openWizard, storedContent(INHERITED))

    expect(await submittedLink(handler)).toEqual(INHERITED)
  })

  it('keeps a stored link that leads nowhere when it edits a widget', async () => {
    const handler = await open(openWizard, storedContent({ type: 'none' }))

    expect(await submittedLink(handler)).toEqual({ type: 'none' })
  })
})
