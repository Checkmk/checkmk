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

function serviceLine(): MapElement {
  return obj({ type: 'line', host_name: 'sw01', service_description: 'Interface 1' })
}

/** What an emptied number input holds: its native v-model keeps the "". */
const EMPTIED = '' as unknown as number

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
    expect(form.label).toMatchObject({ show: false, text: '', size: 11, color: '#ffffff' })
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

  it('keeps the state options a group carries', () => {
    const hostgroup = obj({
      type: 'hostgroup',
      group_name: 'web',
      only_hard_states: true,
      recognize_services: true
    })
    const servicegroup = obj({ type: 'servicegroup', group_name: 'web', only_hard_states: true })

    expect(updatesFromForm(formOf(hostgroup), hostgroup, 'static')).toMatchObject({
      only_hard_states: true,
      recognize_services: true
    })
    const servicegroupUpdates = updatesFromForm(formOf(servicegroup), servicegroup, 'static')
    expect(servicegroupUpdates).toMatchObject({ only_hard_states: true })
    expect(servicegroupUpdates).not.toHaveProperty('recognize_services')
  })

  it('keeps the state options a dynamic group carries', () => {
    const dyngroup = obj({
      type: 'dyngroup',
      object_types: 'host',
      object_filter: 'Filter: groups >= web\n',
      only_hard_states: true,
      recognize_services: true
    })

    expect(updatesFromForm(formOf(dyngroup), dyngroup, 'static')).toMatchObject({
      only_hard_states: true,
      recognize_services: true
    })
  })

  it('leaves service counting alone where the form does not offer it', () => {
    const services = obj({ type: 'dyngroup', object_types: 'service', recognize_services: true })

    expect(updatesFromForm(formOf(services), services, 'static')).not.toHaveProperty(
      'recognize_services'
    )
  })

  it('drops member patterns once the line shows what takes none', () => {
    const line = obj({ type: 'line', line_object_type: 'hostgroup', exclude_members: '^test-' })
    const form = formOf(line)
    form.line_object_type = 'dyngroup'

    expect(updatesFromForm(form, line, 'static').exclude_members).toBeNull()
  })

  it('turns emptied fields into null rather than an empty string', () => {
    const object = obj({ type: 'host', host_name: 'web01', url: 'https://example.com' })
    const form = formOf(object)
    form.url = ''

    expect(updatesFromForm(form, object, 'static').url).toBeNull()
  })

  it('unsets an optional number field that was emptied', () => {
    const object = obj({ type: 'line', line_width: 4 })
    const form = formOf(object)
    form.line_width = EMPTIED

    expect(updatesFromForm(form, object, 'static').line_width).toBeNull()
  })

  it('keeps the stored value of any other number field that was emptied', () => {
    const object = obj({ type: 'host', z: 3 })
    const form = formOf(object)
    form.x = EMPTIED
    form.z = EMPTIED

    expect(updatesFromForm(form, object, 'static')).toMatchObject({ x: 40, z: 3 })
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

  it('keeps a line bound to no host a plain line', () => {
    const object = obj({ type: 'line' })

    expect(updatesFromForm(formOf(object), object, 'static').line_object_type).toBeNull()
  })

  it('keeps a line a service line while its service is still missing', () => {
    const object = obj({ type: 'line', host_name: 'web01' })
    const form = formOf(object)
    form.line_object_type = 'service'

    const updates = updatesFromForm(form, object, 'static')

    expect(updates.line_object_type).toBe('service')
    expect(formOf(obj({ type: 'line', host_name: 'web01', ...updates })).line_object_type).toBe(
      'service'
    )
  })

  it('binds a line like the object it shows, dropping the binding it had', () => {
    const object = obj({ type: 'line', host_name: 'web01', service_description: 'CPU load' })
    const form = formOf(object)
    expect(form.line_object_type).toBe('service')

    form.line_object_type = 'hostgroup'
    form.group_name = 'web'
    form.recognize_services = true

    expect(updatesFromForm(form, object, 'static')).toMatchObject({
      line_object_type: 'hostgroup',
      group_name: 'web',
      recognize_services: true,
      host_name: null,
      service_description: null
    })
  })

  it('stores a line metric only while something reads it', () => {
    const object = serviceLine()
    const form = formOf(object)
    form.weathermap_metric = 'if_in_bps'

    expect(updatesFromForm(form, object, 'static')).not.toHaveProperty('weathermap_metric')

    form.line_weather_color = true
    expect(updatesFromForm(form, object, 'static').weathermap_metric).toBe('if_in_bps')
  })

  it('never stores an outbound metric on its own', () => {
    const object = serviceLine()
    const form = formOf(object)
    form.line_perfdata_label = 'bandwidth'
    form.weathermap_metric_out = 'if_out_bps'

    expect(updatesFromForm(form, object, 'static').weathermap_metric_out).toBeNull()

    form.weathermap_metric = 'if_in_bps'
    expect(updatesFromForm(form, object, 'static').weathermap_metric_out).toBe('if_out_bps')
  })

  it('drops perfdata from a line that shows no service', () => {
    const object = serviceLine()
    const form = formOf(object)
    form.line_weather_color = true
    form.line_object_type = 'hostgroup'

    expect(updatesFromForm(form, object, 'static')).toMatchObject({
      line_perfdata_label: 'none',
      line_weather_color: false
    })
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
    const object = serviceLine()
    const form = formOf(object)
    form.line_weather_color = true

    expect(weatherColorNeedsMetric(form, object)).toBe(true)

    form.weathermap_metric = 'if_in_bps'
    expect(weatherColorNeedsMetric(form, object)).toBe(false)
  })

  it('does not apply to a line that shows no service', () => {
    const object = serviceLine()
    const form = formOf(object)
    form.line_weather_color = true
    form.line_object_type = 'hostgroup'

    expect(weatherColorNeedsMetric(form, object)).toBe(false)
  })

  it('does not apply to anything but a line', () => {
    const object = obj({ type: 'host' })
    const form = formOf(object)
    form.line_weather_color = true

    expect(weatherColorNeedsMetric(form, object)).toBe(false)
  })
})
