/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  formFromObject,
  updatesFromForm,
  weatherColorNeedsMetric
} from '@/maps/map/edit/properties/objectForm'
import type { MapElement, ObjectType } from '@/maps/types/api'

import { anObject } from '../../../support/fixtures'

function obj(extra: Partial<MapElement> & { type: ObjectType }): MapElement {
  return anObject({ id: 'o', x: 40, y: 60, url_target: '_blank', ...extra })
}

function formOf(object: MapElement) {
  return formFromObject(object, { z: 7 })
}

describe('formFromObject', () => {
  it('fills the gaps a stored object leaves', () => {
    const form = formOf(obj({ type: 'host', host_name: 'web01' }))

    expect(form).toMatchObject({
      host_name: 'web01',
      service_description: '',
      line_perfdata_label: 'none',
      url_target: '_blank',
      graph_time_window: 60
    })
    expect(form.label).toMatchObject({ show: true, text: '', size: 11, color: '#ffffff' })
  })

  it("takes the map's stacking default when the object carries no z", () => {
    expect(formOf(obj({ type: 'host' })).z).toBe(7)
    expect(formOf(obj({ type: 'host', z: 3 })).z).toBe(3)
  })

  it('gives a line an end point when it has none yet', () => {
    const form = formOf(obj({ type: 'line', x: 40, y: 60 }))
    expect(form.x2).toBe(190)
    expect(form.y2).toBe(60)
  })
})

describe('updatesFromForm', () => {
  it('sends only the fields the object type carries', () => {
    const object = obj({ type: 'host', host_name: 'web01' })
    const updates = updatesFromForm(formOf(object), object, 'static')

    expect(updates).toMatchObject({
      host_name: 'web01',
      only_hard_states: false,
      recognize_services: false,
      x: 40,
      y: 60
    })
    expect(updates).not.toHaveProperty('service_description')
    expect(updates).not.toHaveProperty('group_name')
  })

  it('turns emptied fields into null rather than an empty string', () => {
    const object = obj({ type: 'host', host_name: 'web01', url: 'https://example.com' })
    const form = formOf(object)
    form.url = ''

    expect(updatesFromForm(form, object, 'static').url).toBeNull()
  })

  it('drops the display block for a graph and a line — neither has an icon', () => {
    for (const type of ['graph', 'line'] as const) {
      const object = obj({ type })
      expect(updatesFromForm(formOf(object), object, 'static').display).toBeNull()
    }
  })

  it('persists coordinates on a canvas map and a position on a geo map', () => {
    const object = obj({ type: 'host', host_name: 'web01', lat: 51, lng: 10 })

    const onCanvas = updatesFromForm(formOf(object), object, 'static')
    expect(onCanvas).toMatchObject({ x: 40, y: 60 })
    expect(onCanvas).not.toHaveProperty('lat')

    const onGeo = updatesFromForm(formOf(object), object, 'worldmap')
    expect(onGeo).toMatchObject({ lat: 51, lng: 10 })
    expect(onGeo).not.toHaveProperty('x')
  })

  it('keeps a line on its own coordinates, geo map or not', () => {
    const object = obj({ type: 'line', x2: 200, y2: 60 })

    expect(updatesFromForm(formOf(object), object, 'static')).toMatchObject({
      x: 40,
      y: 60,
      x2: 200,
      y2: 60
    })
    expect(updatesFromForm(formOf(object), object, 'worldmap')).not.toHaveProperty('x2')
  })

  it('stores a line metric only while something reads it', () => {
    const object = obj({ type: 'line' })
    const form = formOf(object)
    form.weathermap_metric = 'if_in_bps'

    expect(updatesFromForm(form, object, 'static')).not.toHaveProperty('weathermap_metric')

    form.line_weather_color = true
    expect(updatesFromForm(form, object, 'static').weathermap_metric).toBe('if_in_bps')
  })

  it('never stores an outbound metric on its own', () => {
    const object = obj({ type: 'line' })
    const form = formOf(object)
    form.line_perfdata_label = 'bandwidth'
    form.weathermap_metric_out = 'if_out_bps'

    expect(updatesFromForm(form, object, 'static').weathermap_metric_out).toBeNull()

    form.weathermap_metric = 'if_in_bps'
    expect(updatesFromForm(form, object, 'static').weathermap_metric_out).toBe('if_out_bps')
  })

  it('carries a gadget metric only while the object renders as a gadget', () => {
    const object = obj({ type: 'host', host_name: 'web01' })
    const form = formOf(object)
    form.display.gadget_metric = 'load1'

    const asIcon = updatesFromForm(form, object, 'static').display as Record<string, unknown>
    expect(asIcon.gadget_metric).toBeNull()

    form.display.mode = 'gadget'
    const asGadget = updatesFromForm(form, object, 'static').display as Record<string, unknown>
    expect(asGadget).toMatchObject({ gadget_metric: 'load1', gadget_type: 'gauge' })
  })
})

describe('weatherColorNeedsMetric', () => {
  it('holds a line back that is coloured by a metric it does not name', () => {
    const object = obj({ type: 'line' })
    const form = formOf(object)
    form.line_weather_color = true

    expect(weatherColorNeedsMetric(form, object)).toBe(true)

    form.weathermap_metric = 'if_in_bps'
    expect(weatherColorNeedsMetric(form, object)).toBe(false)
  })

  it('does not apply to anything but a line', () => {
    const object = obj({ type: 'host' })
    const form = formOf(object)
    form.line_weather_color = true

    expect(weatherColorNeedsMetric(form, object)).toBe(false)
  })
})
