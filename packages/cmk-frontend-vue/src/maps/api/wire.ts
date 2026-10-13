/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Translation between the REST API's map config and the one the SPA edits.
 *
 * The API groups an object's fields into sub-objects (``position``, ``link``,
 * ``line``, …) and renames some on the way in (``line.style`` for
 * ``line_style``); the editor, the canvas renderer and the property forms all
 * work on one flat object instead. Structural typing cannot bridge a rename, so
 * the mapping is spelled out here — it mirrors the server's own
 * ``_OBJECT_GROUPS`` table in ``cmk.maps.rest_api.utils``, which is where a new
 * field has to be added on both sides.
 */
import type { components as DaemonComponents } from 'cmk-shared-typing/typescript/maps_openapi'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import type {
  MapConfig,
  MapElement,
  MapEnvelope,
  MapPublic,
  MapRead,
  MapView,
  ObjectType,
  PresentationElement
} from '@/maps/types/api'
import { newMapView } from '@/maps/utils/model'

type Schemas = components['schemas']
export type MapListObjectWire = Schemas['MapListObject']
export type MapVisibilityWire = Schemas['MapVisibility']
export type MapConfigWire = Schemas['MapConfig']
type DaemonSchemas = DaemonComponents['schemas']
type MapElementWire = Schemas['MapElement']
type MapViewWire = MapConfigWire['view']
type MapPresentationElementWire = Schemas['MapPresentationView']['elements'][number]

// Transient worldmap auto-source hosts the daemon inflates on every load and
// merges into ``currentMap`` for rendering. They carry synthetic ``auto:*``
// ids (state_service._AUTO_PREFIX) and are explicitly never persisted — saving
// them would freeze the live host set into the stored config (removed hosts
// linger, the config bloats), defeating auto_source.
const AUTO_OBJECT_ID_PREFIX = 'auto:'

// Result of dropping the ``undefined`` members: each key becomes optional and its
// value type loses ``undefined``, so the result satisfies the wire's
// ``exactOptionalPropertyTypes`` optional fields (present ⇒ not ``undefined``).
type Compacted<T> = { [K in keyof T]?: Exclude<T[K], undefined> }

// Drop keys whose value is ``undefined`` so ``json_dump_without_omitted`` on the
// server (and the daemon's flatten step) see a clean body; ``null`` is kept (it
// round-trips a stored ``null``).
function compact<T extends Record<string, unknown>>(obj: T): Compacted<T> {
  return Object.fromEntries(
    Object.entries(obj).filter(([, value]) => value !== undefined)
  ) as Compacted<T>
}

// Every member of the wire sub-object, each allowed to be absent here. Naming the
// sub-object at the call site is what keeps this file honest: a field added to
// the server's ``_OBJECT_GROUPS`` fails the build instead of being silently
// dropped on the next save.
type GroupSource<W> = { [K in keyof Required<W>]: Required<W>[K] | undefined }

// Build a nested wire sub-object, or omit it entirely when none of its members
// are present (the server treats an absent group as its ApiOmitted default).
function group<W extends object>(obj: GroupSource<W>): Compacted<GroupSource<W>> | undefined {
  const compacted = compact({ ...obj })
  return Object.keys(compacted).length > 0 ? compacted : undefined
}

// The object's name label rides in the ``label`` sub-object together with the
// two flat extras (``label_border``/``label_maxlen`` → ``border``/``max_length``).
// A wire label requires its base fields (show/x/y/size/color/background), which
// only the flat ``label`` dict carries, so the group is emitted only when that
// dict is present — matching the daemon's stored default (see
// ``cmk.maps.rest_api.utils._nest_object``).
function labelToWire(obj: MapElement): Schemas['MapObjectLabel'] | undefined {
  if (!obj.label) {
    return undefined
  }
  return {
    ...obj.label,
    ...compact({ border: obj.label_border, max_length: obj.label_maxlen })
  }
}

// Map one FLAT internal object to the nested wire ``MapElement``. Mirrors the
// server's ``_OBJECT_GROUPS`` table in ``cmk.maps.rest_api.utils`` (rest_field ->
// flat_key). ``position`` and ``link`` are always emitted (required on every
// object); the rest are omitted when empty. ``site`` objects are filtered out
// before this runs, so ``type`` never carries the runtime-only ``'site'``.
function objectToWire(obj: MapElement): MapElementWire {
  return {
    id: obj.id,
    type: obj.type as MapElementWire['type'],
    // ``position`` and ``link`` are required on every object (x/y and url_target
    // always present); their optional members ride through ``compact``.
    position: {
      x: obj.x,
      y: obj.y,
      ...compact({ z: obj.z, lat: obj.lat, lng: obj.lng })
    },
    link: {
      url_target: obj.url_target,
      ...compact({
        url: obj.url,
        hover_url: obj.hover_url,
        hover_template: obj.hover_template,
        context_template: obj.context_template
      })
    },
    ...compact({
      image_src: obj.image_src,
      binding: group<Schemas['MapObjectBinding']>({
        connection_id: obj.connection_id,
        host_name: obj.host_name,
        service_description: obj.service_description,
        group_name: obj.group_name,
        map_name: obj.map_name,
        aggregation_id: obj.aggregation_id,
        object_types: obj.object_types,
        object_filter: obj.object_filter,
        only_hard_states: obj.only_hard_states,
        recognize_services: obj.recognize_services,
        expand_depth: obj.expand_depth
      }),
      cmk_label: group<Schemas['MapObjectCmkLabel']>({
        name: obj.cmk_label_name,
        value: obj.cmk_label_value,
        target: obj.cmk_label_target
      }),
      bundle: group<Schemas['MapObjectBundle']>({
        kind: obj.bundle_kind,
        hosts: obj.bundle_hosts,
        precision: obj.bundle_precision
      }),
      line: group<Schemas['MapObjectLine']>({
        x2: obj.x2,
        y2: obj.y2,
        lat2: obj.lat2,
        lng2: obj.lng2,
        mid_x: obj.mid_x,
        mid_y: obj.mid_y,
        start_ref: obj.start_ref,
        end_ref: obj.end_ref,
        style: obj.line_style,
        width: obj.line_width,
        perfdata_label: obj.line_perfdata_label,
        weather_color: obj.line_weather_color,
        metric_in: obj.weathermap_metric,
        metric_out: obj.weathermap_metric_out,
        color: obj.line_color,
        color_border: obj.line_color_border
      }),
      textbox: group<Schemas['MapObjectTextbox']>({
        background: obj.textbox_background,
        border: obj.textbox_border,
        width: obj.textbox_width,
        height: obj.textbox_height
      }),
      graph: group<Schemas['MapObjectGraph']>({
        url: obj.graph_url,
        embed_type: obj.graph_embed_type,
        width: obj.graph_width,
        height: obj.graph_height,
        refresh_interval: obj.graph_refresh_interval,
        metric: obj.graph_metric,
        id: obj.graph_id,
        time_window: obj.graph_time_window
      }),
      filter: group<Schemas['MapObjectFilter']>({
        exclude_members: obj.exclude_members,
        exclude_member_states: obj.exclude_member_states
      }),
      label: labelToWire(obj),
      // ``display`` is nullable in the flat model; a ``null`` means "no config",
      // which the wire expresses by omitting the field (``undefined``).
      display: obj.display ?? undefined
    })
  }
}

// A presentation element's geometry (x/y/w/h/rotation/z/opacity/locked/hidden)
// is FLAT in the SPA but nested under ``transform`` on the wire; every other
// field (kind/id/name/shape/fill/host_name/text/…) stays at the top level.
function elementToWire(el: PresentationElement): MapPresentationElementWire {
  const { x, y, w, h, rotation, z, opacity, locked, hidden, ...rest } = el
  return {
    ...rest,
    transform: { x, y, w, h, rotation, z, opacity, locked, hidden }
  } as MapPresentationElementWire
}

// Only the presentation view differs between flat and wire (its elements nest the
// geometry). Every other view is identical (only ``Map``-prefixed), so it passes
// straight through.
function viewToWire(view: MapView): MapViewWire {
  if (view.type === 'presentation') {
    return { ...view, elements: view.elements.map(elementToWire) }
  }
  return view
}

// The SPA's ``MapConfig`` is the FLAT internal model widened with render-only
// extras: the ``site`` object type and each object's ``site_id`` are client
// constructs the daemon's map schema doesn't model, so they must not be
// persisted. Drop the ``site`` objects (never present at runtime — the daemon
// can't resolve them) and the transient ``auto:*`` worldmap hosts, then convert
// each remaining flat object (and the view) to the nested wire shape the REST
// API expects. ``site_id`` is dropped by ``objectToWire`` (not a wire field).
export function toWireConfig(map: MapConfig): MapConfigWire {
  return {
    // The API requires the fields the daemon's model defaults, so they are
    // spelled out before the spread rather than left to the omitted-means-default
    // rule the API applies to everything else.
    ...map,
    // The API requires this one; the daemon model defaults it, so an unset value
    // has to be spelled out rather than omitted.
    icon_size: map.icon_size ?? null,
    objects: map.objects
      .filter(
        (o): o is MapElement & { type: Exclude<ObjectType, 'site'> } =>
          o.type !== 'site' && !o.id.startsWith(AUTO_OBJECT_ID_PREFIX)
      )
      .map(objectToWire),
    view: viewToWire(map.view)
  }
}

// The map's envelope crosses the wire as a {publish, groups?, hide_in_monitor_menu}
// object; the SPA models the sharing part as the visuals ``MapPublic``
// (false | true | [scope, names]).
export function envelopeToVisibility(envelope: MapEnvelope): MapVisibilityWire {
  const hide = { hide_in_monitor_menu: envelope.hide_in_monitor_menu }
  const p = envelope.public
  if (p === true) {
    return { publish: 'all', ...hide }
  }
  if (Array.isArray(p)) {
    return { publish: p[0], groups: p[1], ...hide }
  }
  return { publish: 'private', ...hide }
}

export function visibilityToPublic(v: MapVisibilityWire): MapPublic {
  if (v.publish === 'all') {
    return true
  }
  if (v.publish === 'contact_groups' || v.publish === 'sites') {
    return [v.publish, v.groups ?? []]
  }
  return false
}

// The REST list returns domain objects ({extensions: {owner, visibility, …,
// summary}}); flatten each into the SPA's ``MapRead`` list row. The summary
// mirrors cmk.maps.gui.store.map_to_read, so this stays in lockstep with
// the page-hydrated home view (which emits MapRead directly).
// Inverse of ``elementToWire`` — hoist the wire ``transform`` back to the flat
// element the SPA renders (used for the list projection's ``view``, whose
// presentation elements arrive nested).
function elementFromWire(el: MapPresentationElementWire): PresentationElement {
  const { transform, ...rest } = el
  return { ...rest, ...transform } as PresentationElement
}

// Inverse of ``viewToWire``: only the presentation view needs its elements
// flattened; every other view passes straight through.
export function viewFromWire(view: MapViewWire): MapView {
  // The API omits a field that holds its default; the editing model requires
  // every field, so the view starts from the defaults and the response fills in
  // what it actually carries.
  const base = newMapView(view.type)
  if (view.type === 'presentation') {
    return { ...base, ...compact(view), elements: view.elements.map(elementFromWire) } as MapView
  }
  return { ...base, ...compact(view) } as MapView
}

export function mapListObjectToRead(obj: MapListObjectWire): MapRead {
  const ext = obj.extensions
  const s = ext.summary
  return {
    name: s.name,
    alias: s.alias,
    connection_id: s.connection_id,
    view_type: s.view_type,
    view: viewFromWire(s.view),
    object_count: s.object_count,
    icon_size: s.icon_size ?? null,
    rotation_interval: s.rotation_interval ?? 0,
    sort_order: s.sort_order ?? 0,
    version: s.version ?? 0,
    hide_in_monitor_menu: ext.visibility.hide_in_monitor_menu,
    render_mode: s.render_mode ?? 'default',
    background_image: s.background_image ?? null,
    background_color: s.background_color ?? null,
    click_action: s.click_action,
    hover_template: s.hover_template ?? null,
    context_template: s.context_template ?? null,
    default_z: s.default_z ?? 1,
    can_edit: ext.can_edit,
    can_delete: ext.can_delete,
    owner: ext.owner,
    is_builtin: ext.is_builtin,
    public: visibilityToPublic(ext.visibility)
  }
}

export function mapRequestBody(
  map: MapConfig,
  envelope?: MapEnvelope
): { config: MapConfigWire; visibility?: MapVisibilityWire } {
  return envelope !== undefined
    ? { config: toWireConfig(map), visibility: envelopeToVisibility(envelope) }
    : { config: toWireConfig(map) }
}

/**
 * The map as the daemon takes it: the same flat shape, minus what only the
 * client knows about. The synthetic ``site`` nodes of a flow map and the
 * transient ``auto:*`` worldmap hosts have no meaning there — the daemon
 * resolves both itself.
 */
export function daemonConfig(map: MapConfig): DaemonSchemas['MapConfig'] {
  return {
    ...map,
    objects: map.objects.filter(
      (o): o is MapElement & { type: Exclude<ObjectType, 'site'> } =>
        o.type !== 'site' && !o.id.startsWith(AUTO_OBJECT_ID_PREFIX)
    )
  }
}
