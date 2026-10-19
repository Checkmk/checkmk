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
import type { HostStateContent, HostStatisticsContent } from '@/dashboard/components/Wizard/types'

const SEARCHHOST: VisualLocation = { type: 'views', name: 'searchhost', owner: '' }
const OWNED_DASHBOARD: VisualLocation = { type: 'dashboards', name: 'linux', owner: 'harry' }
const HOST_STATISTICS_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['siteopt', 'wato_folder', 'hoststate', 'opthostgroup'],
  filter_keys: {},
  single_infos: []
}

function hostStatisticsLink(stored?: HostStatisticsContent['contextual_link']) {
  return useContextualLink<HostStatisticsContent>(HOST_STATISTICS_OPTIONS, stored)
}

const HOST_STATE_OPTIONS: ContextualLinkOptions = {
  modes: ['default', 'inherited', 'custom'],
  filters: ['siteopt', 'wato_folder', 'host', 'host_labels', 'host_tags', 'host_auxtags'],
  filter_keys: {
    host_labels: { type: 'label', object_type: 'host' },
    host_tags: { type: 'tag_group' },
    host_auxtags: { type: 'aux_tag', max_count: 3 }
  },
  single_infos: ['host']
}

function hostStateLink(stored?: HostStateContent['contextual_link']) {
  const handler = useContextualLink<HostStateContent>(HOST_STATE_OPTIONS, stored)
  handler.mode.value = 'custom'
  handler.customLinks.value[0]!.title = 'Same OS'
  handler.customLinks.value[0]!.target = SEARCHHOST
  return handler
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
        includeClickedElement: true,
        filters: [{ id: 1, filterId: 'hoststate', key: null, keyOption: undefined }],
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

  it('carries a label filter with its key', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!

    handler.addFilter(link, 'host_labels')
    link.filters[0]!.key = 'cmk/os_family'

    expect(handler.contextualLink.value).toMatchObject({
      links: [{ filters: [{ filter_id: 'host_labels', key: 'cmk/os_family' }] }]
    })
  })

  it('carries no filter of the clicked element once that is unchecked', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!
    handler.addFilter(link, 'host')

    link.includeClickedElement = false

    expect(handler.contextualLink.value).toMatchObject({ links: [{ filters: [] }] })
  })

  it('reads back a stored keyed filter', () => {
    const stored: HostStateContent['contextual_link'] = {
      type: 'custom',
      links: [
        {
          title: 'Same OS',
          location: SEARCHHOST,
          filters: [{ filter_id: 'host_labels', key: 'cmk/os_family' }, { filter_id: 'host' }],
          include_context: false,
          include_time_range: false,
          show_filter_form: false
        }
      ]
    }

    expect(
      useContextualLink<HostStateContent>(HOST_STATE_OPTIONS, stored).contextualLink.value
    ).toEqual(stored)
  })

  it('rejects a label filter without a key', () => {
    const handler = hostStateLink()

    handler.addFilter(handler.customLinks.value[0]!, 'host_labels')

    expect(handler.validate()).toBe(false)
    expect(handler.contextualLink.value).toBeUndefined()
  })

  it('rejects a label key with a colon', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!
    handler.addFilter(link, 'host_labels')

    link.filters[0]!.key = 'cmk:os'

    expect(handler.validate()).toBe(false)
    expect(handler.validationErrors.value).toEqual(['A label key must not contain a colon.'])
    expect(handler.contextualLink.value).toBeUndefined()
  })

  it('rejects a label filter listed twice with the same key', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!
    handler.addFilter(link, 'host_labels')
    handler.addFilter(link, 'host_labels')

    link.filters[0]!.key = 'env'
    link.filters[1]!.key = 'env'

    expect(handler.validate()).toBe(false)
  })

  it('rejects a label key repeated with a trailing space', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!
    handler.addFilter(link, 'host_labels')
    handler.addFilter(link, 'host_labels')

    link.filters[0]!.key = 'env'
    link.filters[1]!.key = 'env '

    expect(handler.validate()).toBe(false)
  })

  it('accepts one label filter per key', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!
    handler.addFilter(link, 'host_labels')
    handler.addFilter(link, 'host_labels')

    link.filters[0]!.key = 'env'
    link.filters[1]!.key = 'cmk/os_family'

    expect(handler.validate()).toBe(true)
  })

  it('rejects more auxiliary tags than the target filter takes', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!
    for (const auxTag of ['ip-v4', 'ip-v6', 'tcp', 'checkmk-agent']) {
      handler.addFilter(link, 'host_auxtags')
      link.filters.at(-1)!.key = auxTag
    }

    expect(handler.validate()).toBe(false)
    expect(handler.validationErrors.value).toEqual(['A link carries at most 3 auxiliary tags.'])
    expect(handler.contextualLink.value).toBeUndefined()
  })

  it('accepts as many auxiliary tags as the target filter takes', () => {
    const handler = hostStateLink()
    const link = handler.customLinks.value[0]!
    for (const auxTag of ['ip-v4', 'ip-v6', 'tcp']) {
      handler.addFilter(link, 'host_auxtags')
      link.filters.at(-1)!.key = auxTag
    }

    expect(handler.validate()).toBe(true)
  })

  it('accepts an unchecked link whatever the modes hold', () => {
    const handler = hostStatisticsLink()
    handler.mode.value = 'inherited'

    handler.enabled.value = false

    expect(handler.validate()).toBe(true)
  })
})
