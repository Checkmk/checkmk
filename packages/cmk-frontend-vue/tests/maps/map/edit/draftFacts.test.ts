/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import type { NewObjectDraft } from '@/maps/map/composables/useMapEditor'
import { clearDraftBindings, isDraftPlaceable, snapGridSizes } from '@/maps/map/edit/draftFacts'

const _t = ((message: string) => untranslated(message)) as never

function aDraft(overrides: Partial<NewObjectDraft> = {}): NewObjectDraft {
  return {
    type: '',
    host_name: '',
    service_description: '',
    group_name: '',
    map_name: '',
    aggregation_id: '',
    object_types: 'host',
    object_filter: '',
    expand_depth: 0,
    label_text: '',
    image_src: '',
    graph_url: '',
    ...overrides
  }
}

describe('isDraftPlaceable', () => {
  it('refuses a draft with no type picked yet', () => {
    expect(isDraftPlaceable(aDraft())).toBe(false)
  })

  it('needs the binding each type actually shows', () => {
    expect(isDraftPlaceable(aDraft({ type: 'host' }))).toBe(false)
    expect(isDraftPlaceable(aDraft({ type: 'host', host_name: 'web01' }))).toBe(true)
    expect(isDraftPlaceable(aDraft({ type: 'service', host_name: 'web01' }))).toBe(false)
    expect(
      isDraftPlaceable(aDraft({ type: 'service', host_name: 'web01', service_description: 'PING' }))
    ).toBe(true)
    expect(isDraftPlaceable(aDraft({ type: 'hostgroup', group_name: 'linux' }))).toBe(true)
    expect(isDraftPlaceable(aDraft({ type: 'map', map_name: 'other' }))).toBe(true)
    expect(isDraftPlaceable(aDraft({ type: 'aggregation', aggregation_id: 'agg' }))).toBe(true)
    expect(isDraftPlaceable(aDraft({ type: 'image', image_src: 'rack.png' }))).toBe(true)
  })

  it('treats a whitespace-only livestatus filter as unset', () => {
    expect(isDraftPlaceable(aDraft({ type: 'dyngroup', object_filter: '   ' }))).toBe(false)
    expect(
      isDraftPlaceable(aDraft({ type: 'dyngroup', object_filter: 'Filter: host_name ~ ^web' }))
    ).toBe(true)
  })

  it('places the types that carry geometry only', () => {
    for (const type of ['line', 'textbox', 'graph'] as const) {
      expect(isDraftPlaceable(aDraft({ type }))).toBe(true)
    }
  })
})

describe('clearDraftBindings', () => {
  it('drops every binding but keeps the type', () => {
    const draft = aDraft({
      type: 'service',
      host_name: 'web01',
      service_description: 'PING',
      group_name: 'linux',
      map_name: 'other',
      aggregation_id: 'agg',
      expand_depth: 3,
      label_text: 'label',
      image_src: 'rack.png',
      graph_url: 'https://example.com'
    })

    clearDraftBindings(draft)

    expect(draft).toMatchObject({
      type: 'service',
      host_name: '',
      service_description: '',
      group_name: '',
      map_name: '',
      aggregation_id: '',
      expand_depth: 0,
      label_text: '',
      image_src: '',
      graph_url: ''
    })
  })

  it('leaves the livestatus filter alone — it is not cleared by a type switch', () => {
    const draft = aDraft({ type: 'dyngroup', object_filter: 'Filter: x' })
    clearDraftBindings(draft)
    expect(draft.object_filter).toBe('Filter: x')
  })
})

describe('snapGridSizes', () => {
  it('offers off plus the pixel steps, off first', () => {
    expect(snapGridSizes(_t).map((size) => size.value)).toEqual([0, 10, 20, 50])
  })
})
