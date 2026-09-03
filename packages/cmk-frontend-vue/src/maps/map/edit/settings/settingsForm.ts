/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { metadataUpdatesFrom } from '@/maps/shared/metadataForm'
import type {
  FlowView,
  FolderTreeView,
  MapConfig,
  MapRead,
  RadarView,
  WorldmapView
} from '@/maps/types/api'

/** Where a geo map centres when the map itself says nothing. */
const DEFAULT_GEO_VIEW = { lat: 51.0, lng: 10.0, zoom: 5 }

/**
 * Everything the settings form edits outside the FormSpec blocks: the map type
 * and the per-type view fields, flattened into one bag of scalars a form can
 * bind to.
 */
export interface SettingsForm {
  map_type: MapRead['view']['type']
  worldmap_auto_source: '' | 'all_hosts' | 'hostgroup' | 'servicegroup'
  worldmap_auto_filter_value: string
  worldmap_lat: number
  worldmap_lng: number
  worldmap_zoom: number
  worldmap_tile_url: string
  worldmap_tile_saturate: number | undefined
  radar_filter: string
  radar_filter_value: string
  ft_root_folder: string
  ft_default_view: 'list' | 'map'
  ft_default_expand_depth: number
  ft_show_services: boolean
  ft_show_empty_folders: boolean
  ft_problems_only: boolean
  ft_problems_severity: 'any' | 'critical'
  ft_only_hard_states: boolean
  /** Comma-joined, which is the wire shape; the picker works on an id array. */
  ft_sites: string
  background_image: string
  background_color: string
  /** Kept for the save call and the preview patch, edited via FormSpec. */
  alias: string
  connection_id: string
  icon_size: number | null
  rotation_interval: number | null
  click_action: 'link' | 'none'
  show_in_lists: boolean
  hover_template: string
  context_template: string
}

/** The map's stored geo view, or where the parent map is currently looking. */
export function initialGeoView(
  map: MapRead,
  parentView: { lat: number; lng: number; zoom: number } | null | undefined
): { lat: number; lng: number; zoom: number } {
  if (parentView) {
    return { lat: parentView.lat, lng: parentView.lng, zoom: parentView.zoom }
  }
  if (map.view.type === 'worldmap') {
    const view = map.view as WorldmapView
    return { lat: view.lat, lng: view.lng, zoom: view.zoom }
  }
  return { ...DEFAULT_GEO_VIEW }
}

export function formFromMap(
  map: MapRead,
  parentView: { lat: number; lng: number; zoom: number } | null | undefined
): SettingsForm {
  const geo = initialGeoView(map, parentView)
  const worldmap = map.view.type === 'worldmap' ? (map.view as WorldmapView) : null
  const radar = map.view.type === 'radar' ? (map.view as RadarView) : null
  const folderTree = map.view.type === 'foldertree' ? (map.view as FolderTreeView) : null
  return {
    alias: map.alias,
    connection_id: map.connection_id,
    icon_size: map.icon_size,
    rotation_interval: map.rotation_interval,
    click_action: map.click_action ?? 'link',
    show_in_lists: map.show_in_lists !== false,
    map_type: map.view.type,
    worldmap_auto_source: worldmap?.auto_source ?? '',
    worldmap_auto_filter_value: worldmap?.auto_filter_value ?? '',
    worldmap_lat: geo.lat,
    worldmap_lng: geo.lng,
    worldmap_zoom: geo.zoom,
    worldmap_tile_url: worldmap?.tile_url ?? '',
    worldmap_tile_saturate: worldmap?.tile_saturate ?? undefined,
    radar_filter: radar?.filter ?? 'hostgroup',
    radar_filter_value: radar?.filter_value ?? '',
    ft_root_folder: folderTree?.root_folder ?? '',
    ft_default_view: folderTree?.default_view ?? 'list',
    ft_default_expand_depth: folderTree?.default_expand_depth ?? 1,
    ft_show_services: folderTree?.show_services ?? false,
    ft_show_empty_folders: folderTree?.show_empty_folders ?? true,
    ft_problems_only: folderTree?.problems_only ?? false,
    ft_problems_severity: folderTree?.problems_severity ?? 'any',
    ft_only_hard_states: folderTree?.only_hard_states ?? false,
    ft_sites: (folderTree?.sites ?? []).join(', '),
    hover_template: map.hover_template ?? '',
    context_template: map.context_template ?? '',
    background_image: map.background_image ?? '',
    background_color: map.background_color ?? ''
  }
}

/**
 * A flow map's view fields are a FormSpec of their own. Its data bag omits
 * whatever the map does not set: a missing key reads as "use the default",
 * which is what ``FlowView``'s nullable fields mean.
 */
export function flowViewData(map: MapRead): Record<string, unknown> {
  const view = map.view.type === 'flow' ? (map.view as FlowView) : null
  const data: Record<string, unknown> = {}
  if (view?.root) {
    data.root = view.root
  }
  for (const key of [
    'child_layers',
    'parent_layers',
    'top_affected_hosts',
    'max_services_per_host'
  ] as const) {
    const value = view?.[key]
    if (value !== null && value !== undefined) {
      data[key] = value
    }
  }
  return data
}

/**
 * The map's own ``view`` block, rebuilt from the form.
 *
 * A view type carries only its own fields — a stored latitude on a static map
 * would be dead weight that later readers have to second-guess.
 */
export function viewFromForm(
  form: SettingsForm,
  flowView: Record<string, unknown>
): Record<string, unknown> {
  switch (form.map_type) {
    case 'worldmap':
      return {
        type: 'worldmap',
        lat: form.worldmap_lat,
        lng: form.worldmap_lng,
        zoom: form.worldmap_zoom,
        auto_source: form.worldmap_auto_source || null,
        auto_filter_value: form.worldmap_auto_filter_value,
        tile_url: form.worldmap_tile_url || null,
        tile_saturate: form.worldmap_tile_saturate ?? null
      }
    case 'radar':
      return {
        type: 'radar',
        filter: form.radar_filter,
        filter_value: form.radar_filter_value
      }
    case 'flow':
      return {
        type: 'flow',
        root: (flowView.root as string | undefined)?.trim() || null,
        child_layers: (flowView.child_layers as number | null | undefined) ?? null,
        parent_layers: (flowView.parent_layers as number | null | undefined) ?? null,
        top_affected_hosts: (flowView.top_affected_hosts as number | null | undefined) ?? null,
        max_services_per_host: (flowView.max_services_per_host as number | null | undefined) ?? null
      }
    case 'foldertree':
      return {
        type: 'foldertree',
        root_folder: form.ft_root_folder.trim(),
        default_view: form.ft_default_view,
        default_expand_depth: form.ft_default_expand_depth,
        show_services: form.ft_show_services,
        show_empty_folders: form.ft_show_empty_folders,
        problems_only: form.ft_problems_only,
        problems_severity: form.ft_problems_severity,
        only_hard_states: form.ft_only_hard_states,
        sites: form.ft_sites
          .split(',')
          .map((site) => site.trim())
          .filter(Boolean)
      }
    default:
      return { type: form.map_type }
  }
}

/**
 * What the preview iframe needs to repaint the map as the form currently
 * describes it.
 *
 * A presentation map is designed on its own canvas, so patching a
 * metadata-only ``view`` onto it would blank the slide.
 */
export function previewPatch(
  form: SettingsForm,
  formSpec: Record<string, unknown>,
  flowView: Record<string, unknown>,
  fallbackAlias: string
): Record<string, unknown> {
  return {
    alias: (formSpec.alias as string) ?? fallbackAlias,
    icon_size: (formSpec.icon_size as number | null | undefined) ?? null,
    hover_template: (formSpec.hover_template as string) ?? '',
    context_template: (formSpec.context_template as string) ?? '',
    background_color: form.background_color || null,
    ...(form.map_type === 'presentation' ? {} : { view: viewFromForm(form, flowView) })
  }
}

/**
 * The metadata FormSpec's data bag.
 *
 * An optional field the map does not set is left out entirely: the dispatcher
 * then renders it unchecked, which reads as "inherit the global default".
 * Sending '' or null instead would show an enabled override with nothing in
 * it. Two fields also change shape here — ``click_action`` is a boolean choice
 * in the form but 'link'/'none' on the wire, and ``rotation_interval`` a
 * cascading choice but a plain number — and are flattened back on save.
 */
export function metadataFormData(map: MapRead): Record<string, unknown> {
  const rotation = map.rotation_interval ?? 0
  const data: Record<string, unknown> = {
    alias: map.alias,
    connection_id: map.connection_id,
    rotation_interval: rotation > 0 ? ['every', rotation] : ['off', null],
    click_action: map.click_action !== 'none',
    render_mode: map.render_mode ?? 'default',
    default_z: map.default_z ?? 1,
    show_in_lists: map.show_in_lists !== false
  }
  if (map.icon_size !== null) {
    data.icon_size = map.icon_size
  }
  if (map.hover_template) {
    data.hover_template = map.hover_template
  }
  if (map.context_template) {
    data.context_template = map.context_template
  }
  return data
}

/**
 * Metadata fields that have no effect for a given map type, and are therefore
 * not offered: a radar or folder-tree map has no hover popups, and neither it
 * nor a presentation has coordinate-positioned icons for icon size, layer or
 * rendering mode to act on.
 */
export function hiddenMetadataFields(mapType: MapRead['view']['type']): Set<string> {
  switch (mapType) {
    case 'radar':
      return new Set(['hover_template', 'context_template'])
    case 'foldertree':
      return new Set([
        'icon_size',
        'default_z',
        'render_mode',
        'hover_template',
        'context_template'
      ])
    case 'presentation':
      // Slide design lives on the canvas; only identification, connection,
      // rotation and show-in-lists apply here.
      return new Set([
        'icon_size',
        'default_z',
        'render_mode',
        'hover_template',
        'context_template',
        'click_action'
      ])
    default:
      return new Set()
  }
}

/**
 * The same for the single-map form, which describes the whole map rather than a
 * selection of fields.
 *
 * Its optional fields — the icon-size override and the two templates — mean
 * "no override" when they are left unticked, so they are named as null instead
 * of being left out.
 */
export function metadataOverridesFrom(values: Record<string, unknown>): Partial<MapConfig> {
  return {
    icon_size: null,
    hover_template: null,
    context_template: null,
    ...metadataUpdatesFrom(values)
  }
}
