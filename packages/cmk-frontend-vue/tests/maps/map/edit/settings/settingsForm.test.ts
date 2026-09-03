/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  flowViewData,
  formFromMap,
  hiddenMetadataFields,
  initialGeoView,
  metadataFormData,
  metadataOverridesFrom,
  previewPatch,
  viewFromForm
} from '@/maps/map/edit/settings/settingsForm'
import type { MapRead, MapView } from '@/maps/types/api'

import { newMapView } from '../../../support/fixtures'

function aMapRead(overrides: Partial<MapRead> = {}): MapRead {
  return {
    name: 'net-overview',
    alias: 'Network Overview',
    icon_size: null,
    connection_id: 'local',
    view_type: 'static',
    view: newMapView('static'),
    object_count: 0,
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    can_delete: true,
    public: false,
    ...overrides
  }
}

function geoMap(view: Partial<MapView> = {}): MapRead {
  return aMapRead({
    view_type: 'worldmap',
    view: { ...newMapView('worldmap'), lat: 48.1, lng: 11.6, zoom: 9, ...view } as MapView
  })
}

describe('initialGeoView', () => {
  it("prefers the parent map's current view over the stored one", () => {
    expect(initialGeoView(geoMap(), { lat: 1, lng: 2, zoom: 3 })).toEqual({
      lat: 1,
      lng: 2,
      zoom: 3
    })
  })

  it('falls back to the stored view, then to a default', () => {
    expect(initialGeoView(geoMap(), null)).toEqual({ lat: 48.1, lng: 11.6, zoom: 9 })
    expect(initialGeoView(aMapRead(), null)).toEqual({ lat: 51, lng: 10, zoom: 5 })
  })
})

describe('formFromMap', () => {
  it('joins the folder-tree sites into the wire shape', () => {
    const map = aMapRead({
      view_type: 'foldertree',
      view: { ...newMapView('foldertree'), sites: ['heute', 'remote'] } as MapView
    })
    expect(formFromMap(map, null).ft_sites).toBe('heute, remote')
  })

  it('reads the type-specific fields of the view the map actually has', () => {
    const form = formFromMap(geoMap({ tile_url: 'https://tiles/{z}' } as Partial<MapView>), null)
    expect(form).toMatchObject({
      map_type: 'worldmap',
      worldmap_tile_url: 'https://tiles/{z}',
      radar_filter: 'hostgroup'
    })
  })
})

describe('viewFromForm', () => {
  it('carries only the picked type’s own fields', () => {
    const form = formFromMap(geoMap(), null)
    expect(viewFromForm(form, {})).toEqual({
      type: 'worldmap',
      lat: 48.1,
      lng: 11.6,
      zoom: 9,
      auto_source: null,
      auto_filter_value: '',
      tile_url: null,
      tile_saturate: null
    })
  })

  it('splits the folder-tree sites back apart, dropping the blanks', () => {
    const form = formFromMap(
      aMapRead({ view_type: 'foldertree', view: newMapView('foldertree') }),
      null
    )
    form.ft_sites = ' heute , , remote '
    expect(viewFromForm(form, {}).sites).toEqual(['heute', 'remote'])
  })

  it('reads a flow view out of its own FormSpec bag', () => {
    const form = formFromMap(aMapRead({ view_type: 'flow', view: newMapView('flow') }), null)
    expect(viewFromForm(form, { root: '  web01  ', child_layers: 2 })).toMatchObject({
      type: 'flow',
      root: 'web01',
      child_layers: 2,
      parent_layers: null
    })
  })

  it('names nothing but the type for a map without view fields', () => {
    expect(viewFromForm(formFromMap(aMapRead(), null), {})).toEqual({ type: 'static' })
  })
})

describe('flowViewData', () => {
  it('leaves out what the map does not set, so it reads as "use the default"', () => {
    const map = aMapRead({
      view_type: 'flow',
      view: { ...newMapView('flow'), root: 'web01', child_layers: null } as MapView
    })
    expect(flowViewData(map)).toEqual({ root: 'web01' })
  })
})

describe('metadataFormData', () => {
  it('omits an unset optional field rather than sending an empty override', () => {
    const data = metadataFormData(aMapRead({ icon_size: null }))
    expect(data).not.toHaveProperty('icon_size')
    expect(data).not.toHaveProperty('hover_template')
  })

  it('reshapes the two fields whose form and wire shapes differ', () => {
    expect(metadataFormData(aMapRead({ rotation_interval: 30 })).rotation_interval).toEqual([
      'every',
      30
    ])
    expect(metadataFormData(aMapRead({ rotation_interval: 0 })).rotation_interval).toEqual([
      'off',
      null
    ])
    expect(metadataFormData(aMapRead({ click_action: 'none' })).click_action).toBe(false)
  })
})

describe('metadataOverridesFrom', () => {
  it('names an absent optional field as no override', () => {
    const overrides = metadataOverridesFrom({ alias: 'Network Overview' })

    expect(overrides.icon_size).toBeNull()
    expect(overrides.hover_template).toBeNull()
    expect(overrides.context_template).toBeNull()
  })
})

describe('hiddenMetadataFields', () => {
  it('hides the popups a radar map has no objects to show them on', () => {
    expect([...hiddenMetadataFields('radar')]).toEqual(['hover_template', 'context_template'])
  })

  it('hides everything about icons where nothing is placed by coordinate', () => {
    expect(hiddenMetadataFields('foldertree')).toContain('icon_size')
    expect(hiddenMetadataFields('presentation')).toContain('click_action')
  })

  it('hides nothing on a static map', () => {
    expect(hiddenMetadataFields('static').size).toBe(0)
  })
})

describe('previewPatch', () => {
  it('leaves the view out for a presentation, whose slides own it', () => {
    const map = aMapRead({ view_type: 'presentation', view: newMapView('presentation') })
    const patch = previewPatch(formFromMap(map, null), {}, {}, map.alias)
    expect(patch).not.toHaveProperty('view')
    expect(patch.alias).toBe('Network Overview')
  })

  it('prefers what the FormSpec holds over the map it was opened on', () => {
    const patch = previewPatch(
      formFromMap(aMapRead(), null),
      { alias: 'Edited', icon_size: 48 },
      {},
      'Network Overview'
    )
    expect(patch).toMatchObject({ alias: 'Edited', icon_size: 48 })
  })
})
