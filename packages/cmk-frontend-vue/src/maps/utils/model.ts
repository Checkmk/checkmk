/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Building map objects and states on the client.
 *
 * Several surfaces synthesise these: the BI subtree renders nodes the map never
 * stored, the radar canvas turns live states into placeable objects, the settings
 * preview fakes one of each. The server always sends every field, so the models
 * require them all — which is right for what is received and unhelpful for what
 * is built here. These fill in the same defaults the server would.
 */
import type { FolderTreeView, MapElement, MapView, ObjectState } from '@/maps/types/api'

/** A map object with the defaults an unset field carries server-side. */
export function newMapElement(
  fields: Partial<MapElement> & Pick<MapElement, 'id' | 'type'>
): MapElement {
  return {
    x: 0,
    y: 0,
    url_target: '_blank',
    line_perfdata_label: 'none',
    line_weather_color: false,
    only_hard_states: false,
    recognize_services: false,
    expand_depth: 0,
    graph_embed_type: 'img',
    graph_width: 400,
    graph_height: 200,
    graph_refresh_interval: 0,
    // Both are ``| null`` on the wire: no per-object override, render with the map's defaults.
    label: null,
    display: null,
    ...fields
  }
}

/** A monitoring state with the defaults the daemon would have sent. */
export function newObjectState(
  fields: Partial<ObjectState> & Pick<ObjectState, 'object_id' | 'type' | 'state'>
): ObjectState {
  return {
    output: '',
    perf_data: '',
    check_command: '',
    acknowledged: false,
    in_downtime: false,
    stale: false,
    notifications_enabled: true,
    active_checks_enabled: true,
    address: '',
    alias: '',
    state_type: '',
    current_attempt: 0,
    max_attempts: 0,
    ...fields
  }
}

/**
 * The view a map of the given type starts with, matching the server's own
 * defaults for every field so a map created here and one created through the API
 * render identically.
 */
export function newMapView(mapType: 'foldertree'): FolderTreeView
export function newMapView(mapType: string): MapView
export function newMapView(mapType: string): MapView {
  switch (mapType) {
    case 'worldmap':
      return {
        type: 'worldmap',
        lat: 51.0,
        lng: 10.0,
        zoom: 5,
        auto_filter_value: '',
        problems_only: false
      }
    case 'radar':
      return { type: 'radar', filter: 'hostgroup', filter_value: '', problems_only: false }
    case 'flow':
      return { type: 'flow', positions: {}, problems_only: false }
    case 'foldertree':
      return {
        type: 'foldertree',
        root_folder: '',
        sites: [],
        show_empty_folders: true,
        show_services: false,
        only_hard_states: false,
        default_view: 'map',
        default_expand_depth: 1,
        problems_severity: 'any',
        problems_only: false
      }
    case 'presentation':
      // A slide stage with the daemon's defaults; elements are added on the canvas.
      return {
        type: 'presentation',
        width: 1920,
        height: 1080,
        theme: 'midnight',
        elements: [],
        problems_only: false
      }
    default:
      return { type: 'static', problems_only: false }
  }
}
