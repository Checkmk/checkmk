/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import type {
  ContextualLinkOptions,
  VisualLocation
} from '@/dashboard/components/Wizard/components/ContextualLink/contextualLink'
import { useContextualLink } from '@/dashboard/components/Wizard/components/ContextualLink/useContextualLink'
import type { HostStatisticsContent } from '@/dashboard/components/Wizard/types'

const SEARCHHOST: VisualLocation = { type: 'views', name: 'searchhost', owner: '' }
const OWNED_DASHBOARD: VisualLocation = { type: 'dashboards', name: 'linux', owner: 'harry' }
const HOST_STATISTICS_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['siteopt', 'wato_folder', 'hoststate', 'opthostgroup'],
  single_infos: []
}

function hostStatisticsLink(stored?: HostStatisticsContent['contextual_link']) {
  return useContextualLink<HostStatisticsContent>(HOST_STATISTICS_OPTIONS, stored)
}

describe('useContextualLink', () => {
  it('keeps the built-in link of a new widget', () => {
    expect(hostStatisticsLink().contextualLink.value).toEqual({ type: 'default' })
  })

  it('links nowhere when unchecked', () => {
    const handler = hostStatisticsLink()

    handler.enabled.value = false

    expect(handler.contextualLink.value).toEqual({ type: 'none' })
  })

  it('pins the context and the closed filter form of an inherited link', () => {
    const handler = hostStatisticsLink()

    handler.mode.value = 'inherited'
    handler.inheritedTarget.value = OWNED_DASHBOARD

    expect(handler.contextualLink.value).toEqual({
      type: 'inherited',
      location: OWNED_DASHBOARD,
      include_context: true,
      include_time_range: true,
      show_filter_form: false
    })
  })

  it('builds a custom link from its entries', () => {
    const handler = hostStatisticsLink()

    handler.mode.value = 'custom'
    handler.customLinks.value = [
      {
        id: 0,
        title: 'Down hosts',
        target: SEARCHHOST,
        filters: ['hoststate'],
        includeContext: false,
        includeTimeRange: true,
        showFilterForm: false
      }
    ]

    expect(handler.contextualLink.value).toEqual({
      type: 'custom',
      links: [
        {
          title: 'Down hosts',
          location: SEARCHHOST,
          filters: [{ filter_id: 'hoststate' }],
          include_context: false,
          include_time_range: true,
          show_filter_form: false
        }
      ]
    })
  })

  it('keeps the inherited target while another mode is picked', () => {
    const handler = hostStatisticsLink()
    handler.mode.value = 'inherited'
    handler.inheritedTarget.value = SEARCHHOST

    handler.mode.value = 'custom'
    handler.mode.value = 'inherited'

    expect(handler.contextualLink.value).toMatchObject({ location: SEARCHHOST })
  })

  it('reads back a stored custom link', () => {
    const stored: HostStatisticsContent['contextual_link'] = {
      type: 'custom',
      links: [
        {
          title: 'Down hosts',
          location: OWNED_DASHBOARD,
          filters: [{ filter_id: 'wato_folder' }],
          include_context: true,
          include_time_range: false,
          show_filter_form: true
        }
      ]
    }

    expect(hostStatisticsLink(stored).contextualLink.value).toEqual(stored)
  })

  it('rejects an inherited link without a target', () => {
    const handler = hostStatisticsLink()
    handler.mode.value = 'inherited'

    expect(handler.validate()).toBe(false)
    expect(handler.contextualLink.value).toBeUndefined()
  })

  it('clears its error once the missing target is picked', async () => {
    const handler = hostStatisticsLink()
    handler.mode.value = 'inherited'
    handler.validate()

    handler.inheritedTarget.value = SEARCHHOST
    await nextTick()

    expect(handler.validationErrors.value).toEqual([])
  })

  it('rejects a custom link entry without a title', () => {
    const handler = hostStatisticsLink()
    handler.mode.value = 'custom'
    handler.customLinks.value[0]!.target = SEARCHHOST

    expect(handler.validate()).toBe(false)
  })

  it('rejects a custom link without entries', () => {
    const handler = hostStatisticsLink()
    handler.mode.value = 'custom'

    handler.removeCustomLink(0)

    expect(handler.validate()).toBe(false)
  })

  it('accepts an unchecked link whatever the modes hold', () => {
    const handler = hostStatisticsLink()
    handler.mode.value = 'inherited'

    handler.enabled.value = false

    expect(handler.validate()).toBe(true)
  })
})
