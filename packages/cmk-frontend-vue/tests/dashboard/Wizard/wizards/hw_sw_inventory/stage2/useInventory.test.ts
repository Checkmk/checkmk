/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import type { InventoryContent, WidgetProps } from '@/dashboard/components/Wizard/types'
import {
  type UseInventory,
  useInventory
} from '@/dashboard/components/Wizard/wizards/hw_sw_inventory/stage2/InventoryWidget/useInventory'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { DashboardConstants } from '@/dashboard/types/dashboard'

type InventoryLink = InventoryContent['contextual_link']

const API = `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions`

const CONSTANTS: DashboardConstants = {
  responsive_grid_breakpoints: {},
  widgets: {
    inventory: {
      filter_context: { restricted_to_single: ['host'] },
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
  }
}

const INHERITED: InventoryLink = {
  type: 'inherited',
  location: { type: 'dashboards', name: 'main', owner: null },
  include_context: false,
  include_time_range: false,
  show_filter_form: false
}

const server = setupServer(
  http.post(`${API}/compute-widget-titles/invoke`, () =>
    HttpResponse.json({ extensions: { titles: { preview_widget: 'Inventory' } } })
  ),
  http.post(`${API}/compute-widget-attributes/invoke`, () =>
    HttpResponse.json({ value: { filter_context: { uses_infos: ['host'] } } })
  )
)

function storedInventory(contextualLink: InventoryLink): WidgetProps {
  return {
    content: { type: 'inventory', path: '.hardware.cpu.cores', contextual_link: contextualLink },
    effectiveTitle: 'Inventory',
    effective_filter_context: { filters: {}, uses_infos: ['host'], restricted_to_single: [] },
    general_settings: {
      title: { text: 'Inventory', render_mode: 'with_background' },
      render_background: true
    }
  }
}

async function openInventory(currentSpec: WidgetProps | null = null): Promise<UseInventory> {
  let handler: Promise<UseInventory> | undefined
  const consumer = defineComponent({
    setup() {
      handler = useInventory(ref('.hardware.cpu.cores'), {}, currentSpec)
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

async function submittedLink(handler: UseInventory): Promise<InventoryContent['contextual_link']> {
  const { content } = await handler.getSubmitProps()
  if (content.type !== 'inventory') {
    throw new Error(`The wizard submitted a ${content.type} widget.`)
  }
  return content.contextual_link
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('useInventory', () => {
  it('submits a selected target as an inherited link without context and filter form', async () => {
    const handler = await openInventory()

    handler.linkType.value = 'views'
    await nextTick()
    handler.linkTarget.value = { name: 'host', owner: '' }

    expect(await submittedLink(handler)).toEqual({
      type: 'inherited',
      location: { type: 'views', name: 'host', owner: '' },
      include_context: false,
      include_time_range: false,
      show_filter_form: false
    })
  })

  it('shows the target of a stored inherited link in the target selectors', async () => {
    const handler = await openInventory(storedInventory(INHERITED))

    expect(handler.linkType.value).toBe('dashboards')
    expect(handler.linkTarget.value).toEqual({ name: 'main', owner: null })
  })

  it('submits the default link once the target of a stored inherited link is cleared', async () => {
    const handler = await openInventory(storedInventory(INHERITED))

    handler.linkType.value = null

    expect(await submittedLink(handler)).toEqual({ type: 'default' })
  })
})
