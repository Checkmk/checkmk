/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { LinePerfdataLabel, MapElement, MapViewType } from '@/maps/types/api'

/**
 * How a label is aligned. The wire model also knows 'justify', which the card
 * does not offer but must not drop from an object that carries it.
 */
type LabelAlign = NonNullable<NonNullable<MapElement['label']>['align']> | null

/** Defaults an object inherits from the map it sits on. */
export interface ObjectFormDefaults {
  /** The map's stacking default, used for an object that carries no z. */
  z: number
}

/**
 * Every property the card can edit, with the gaps in a map object filled in.
 *
 * The wire model omits what is unset, but a form field cannot bind to
 * ``undefined`` — so the form is total and ``updatesFromForm`` turns the
 * emptiness back into the nulls the API expects.
 */
export interface ObjectForm {
  connection_id: string
  host_name: string
  service_description: string
  group_name: string
  map_name: string
  aggregation_id: string
  object_types: 'host' | 'service'
  object_filter: string
  expand_depth: number
  line_style: string | null
  line_color: string | null
  line_color_border: string | null
  line_width: number | undefined
  line_perfdata_label: LinePerfdataLabel
  line_weather_color: boolean
  label: {
    show: boolean
    text: string
    x: number
    y: number
    size: number
    color: string
    background: string
    align: LabelAlign
  }
  label_border: string | null
  label_maxlen: number | undefined
  textbox_background: string | null
  textbox_border: string | null
  textbox_width: number | undefined
  textbox_height: number | undefined
  graph_url: string
  graph_embed_type: 'img' | 'iframe'
  graph_width: number
  graph_height: number
  graph_refresh_interval: number
  graph_metric: string[]
  graph_id: string | null
  graph_time_window: number
  display: {
    mode: 'icon' | 'text' | 'gadget'
    image: string
    image_size: number | undefined
    gadget_type: string
    gadget_metric: string
  }
  weathermap_metric: string
  weathermap_metric_out: string
  only_hard_states: boolean
  recognize_services: boolean
  exclude_members: string
  exclude_member_states: string
  url: string
  url_target: string
  hover_url: string
  hover_template: string
  context_template: string
  x: number
  y: number
  lat: number
  lng: number
  z: number
  x2: number
  y2: number
}

const DEFAULT_LABEL_SIZE = 11
const DEFAULT_LABEL_COLOR = '#ffffff'
const DEFAULT_GRAPH_WIDTH = 400
const DEFAULT_GRAPH_HEIGHT = 200
const DEFAULT_GRAPH_TIME_WINDOW = 60
/** How far a new line reaches when the object carries no end point yet. */
const LINE_DEFAULT_LENGTH = 150

/** The object as the form sees it. */
export function formFromObject(object: MapElement, defaults: ObjectFormDefaults): ObjectForm {
  return {
    connection_id: object.connection_id ?? '',
    host_name: object.host_name ?? '',
    service_description: object.service_description ?? '',
    group_name: object.group_name ?? '',
    map_name: object.map_name ?? '',
    aggregation_id: object.aggregation_id ?? '',
    object_types: object.object_types ?? 'host',
    object_filter: object.object_filter ?? '',
    expand_depth: object.expand_depth ?? 0,
    line_style: object.line_style ?? null,
    line_color: object.line_color ?? null,
    line_color_border: object.line_color_border ?? null,
    line_width: object.line_width ?? undefined,
    line_perfdata_label: object.line_perfdata_label ?? 'none',
    line_weather_color: object.line_weather_color ?? false,
    label: {
      show: object.label?.show ?? true,
      text: object.label?.text ?? '',
      x: object.label?.x ?? 0,
      y: object.label?.y ?? 0,
      size: object.label?.size ?? DEFAULT_LABEL_SIZE,
      color: object.label?.color ?? DEFAULT_LABEL_COLOR,
      background: object.label?.background ?? 'transparent',
      align: object.label?.align ?? null
    },
    label_border: object.label_border ?? null,
    label_maxlen: object.label_maxlen ?? undefined,
    textbox_background: object.textbox_background ?? null,
    textbox_border: object.textbox_border ?? null,
    textbox_width: object.textbox_width ?? undefined,
    textbox_height: object.textbox_height ?? undefined,
    graph_url: object.graph_url ?? '',
    graph_embed_type: object.graph_embed_type ?? 'img',
    graph_width: object.graph_width ?? DEFAULT_GRAPH_WIDTH,
    graph_height: object.graph_height ?? DEFAULT_GRAPH_HEIGHT,
    graph_refresh_interval: object.graph_refresh_interval ?? 0,
    graph_metric: object.graph_metric ?? [],
    graph_id: object.graph_id ?? null,
    graph_time_window: object.graph_time_window ?? DEFAULT_GRAPH_TIME_WINDOW,
    display: {
      mode: object.display?.mode ?? 'icon',
      image: object.display?.image ?? '',
      image_size: object.display?.image_size ?? undefined,
      gadget_type: object.display?.gadget_type ?? 'gauge',
      gadget_metric: object.display?.gadget_metric ?? ''
    },
    weathermap_metric: object.weathermap_metric ?? '',
    weathermap_metric_out: object.weathermap_metric_out ?? '',
    only_hard_states: object.only_hard_states ?? false,
    recognize_services: object.recognize_services ?? false,
    exclude_members: object.exclude_members ?? '',
    exclude_member_states: object.exclude_member_states ?? '',
    url: object.url ?? '',
    url_target: object.url_target ?? '_blank',
    hover_url: object.hover_url ?? '',
    hover_template: object.hover_template ?? '',
    context_template: object.context_template ?? '',
    x: object.x ?? 0,
    y: object.y ?? 0,
    lat: object.lat ?? 0,
    lng: object.lng ?? 0,
    z: object.z ?? defaults.z,
    x2: object.x2 ?? object.x + LINE_DEFAULT_LENGTH,
    y2: object.y2 ?? object.y
  }
}

/**
 * The patch to send for an edited object.
 *
 * Only what the object's own type can carry is included: a hostname on a
 * textbox, or line coordinates on a worldmap object, would be stored and then
 * silently ignored by every renderer. Empty strings become null so that
 * clearing a field really unsets it rather than storing "".
 */
export function updatesFromForm(
  form: ObjectForm,
  object: MapElement,
  mapType: MapViewType | undefined
): Record<string, unknown> {
  const type = object.type
  const updates: Record<string, unknown> = {
    connection_id: form.connection_id || null,
    // A graph or a line has no icon, and a stored display block would outlive
    // a later type change.
    display:
      type === 'graph' || type === 'line'
        ? null
        : {
            mode: form.display.mode,
            image: form.display.image || null,
            image_size: form.display.image_size ?? null,
            gadget_type: form.display.mode === 'gadget' ? form.display.gadget_type : null,
            gadget_metric:
              form.display.mode === 'gadget' ? form.display.gadget_metric || null : null
          },
    label: {
      show: form.label.show,
      text: form.label.text || null,
      x: form.label.x,
      y: form.label.y,
      size: form.label.size,
      color: form.label.color,
      background: form.label.background,
      align: form.label.align
    },
    label_border: form.label_border || null,
    label_maxlen: form.label_maxlen ?? null,
    textbox_background: form.textbox_background || null,
    textbox_border: form.textbox_border || null,
    textbox_width: form.textbox_width ?? null,
    textbox_height: form.textbox_height ?? null,
    graph_url: form.graph_url || null,
    graph_embed_type: form.graph_embed_type,
    graph_width: form.graph_width,
    graph_height: form.graph_height,
    graph_refresh_interval: form.graph_refresh_interval,
    graph_metric: form.graph_metric.length ? form.graph_metric : null,
    graph_id: form.graph_id || null,
    graph_time_window: form.graph_time_window,
    line_style: form.line_style,
    line_color: form.line_color || null,
    line_color_border: form.line_color_border || null,
    line_width: form.line_width ?? null,
    line_perfdata_label: form.line_perfdata_label,
    line_weather_color: form.line_weather_color,
    url: form.url || null,
    url_target: form.url_target,
    hover_url: form.hover_url || null,
    hover_template: form.hover_template || null,
    context_template: form.context_template || null,
    exclude_members: form.exclude_members || null,
    exclude_member_states: form.exclude_member_states || null,
    z: form.z
  }

  if (type === 'host' || type === 'service') {
    updates.host_name = form.host_name || null
    updates.only_hard_states = form.only_hard_states
  }
  if (type === 'host') {
    updates.recognize_services = form.recognize_services
  }
  if (type === 'service') {
    updates.service_description = form.service_description || null
  }
  if (type === 'graph') {
    updates.host_name = form.host_name || null
    updates.service_description = form.service_description || null
  }
  if (type === 'hostgroup' || type === 'servicegroup') {
    updates.group_name = form.group_name || null
  }
  if (type === 'map') {
    updates.map_name = form.map_name || null
  }
  if (type === 'aggregation') {
    updates.aggregation_id = form.aggregation_id || null
    updates.expand_depth = form.expand_depth ?? 0
  }
  if (type === 'dyngroup') {
    updates.object_types = form.object_types
    updates.object_filter = form.object_filter || null
  }

  if (type === 'line') {
    updates.host_name = form.host_name || null
    updates.service_description = form.service_description || null
    // The metric is what perfdata labels and weather colouring look up, so it
    // is stored exactly while one of them is on.
    if (form.line_perfdata_label !== 'none' || form.line_weather_color) {
      updates.weathermap_metric = form.weathermap_metric || null
      // The outbound metric is the second direction of the first one; on its
      // own it would colour the inbound half from an arbitrary metric.
      updates.weathermap_metric_out = (form.weathermap_metric && form.weathermap_metric_out) || null
    }
    if (mapType !== 'worldmap') {
      updates.x = form.x
      updates.y = form.y
      updates.x2 = form.x2
      updates.y2 = form.y2
    }
  } else if (mapType === 'worldmap') {
    updates.lat = form.lat
    updates.lng = form.lng
  } else {
    updates.x = form.x
    updates.y = form.y
  }

  return updates
}

/**
 * Whether the form still needs a metric before it can be saved: weather
 * colouring has nothing to colour a line by without one.
 */
export function weatherColorNeedsMetric(form: ObjectForm, object: MapElement): boolean {
  return object.type === 'line' && form.line_weather_color && !form.weathermap_metric.trim()
}
