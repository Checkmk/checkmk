/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * TypeScript types for the Maps SPA.
 *
 * Everything the SPA receives over the wire is aliased from a generated schema,
 * never declared here: the map configuration and the GUI-owned lookups from the
 * Checkmk REST API (``openapi_internal``, generated from the
 * ``cmk.maps.rest_api`` models), live state, topology and the stream frames from
 * the Maps daemon (``maps_openapi``, generated from its FastAPI app). What stays
 * below are the SPA's own shapes: the flat editing model the renderer works on,
 * and types for state that never leaves the browser.
 */
import type { components as DaemonComponents } from 'cmk-shared-typing/typescript/maps_openapi'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

type Schemas = components['schemas']
type Daemon = DaemonComponents['schemas']

// The object types the daemon knows, plus ``site``: the Flow Map's synthetic
// per-site umbrella node, which never persists but flows through the same object
// model at runtime.
export type ObjectType = Daemon['MapElement']['type'] | 'site'

export type AggregationInfo = Schemas['MapsAggregation']

// A node of a BI hierarchy. The daemon carries it on an object's state, the REST
// tree endpoint returns its own (structurally identical) model, so the daemon
// alias types both.
export type AggregationNode = Daemon['AggregationNode']

// Per-branch BI state from the maps_aggregation show-states endpoint: the raw
// cmk.bi result (integer state), which the states service maps into an ObjectState.
export type AggregationStateRaw = Schemas['MapsAggregationState']

// The daemon-flat object label dict. The wire ``MapObjectLabel`` also carries
// ``border``/``max_length``, but those live as separate flat fields on
// ``MapElement`` (``label_border``/``label_maxlen``), so drop them here.
export type LabelConfig = Daemon['LabelConfig']

export type DisplayConfig = Daemon['DisplayConfig']

export type LineStyle = NonNullable<Daemon['MapElement']['line_style']>

export type LinePerfdataLabel = Daemon['MapElement']['line_perfdata_label']

export type ServiceLayout = NonNullable<Daemon['FlowView']['service_layout']>

// The views a map can carry. The daemon holds the map in the shape the SPA edits
// it in, so these come from its schema, not from the REST API's nested one.
export type StaticView = Daemon['StaticView']
export type WorldmapView = Daemon['WorldmapView']
export type RadarView = Daemon['RadarView']
export type FlowNodePosition = Daemon['FlowNodePosition']
export type FlowView = Daemon['FlowView']
export type FolderTreeView = Daemon['FolderTreeView']
export type PresentationView = Daemon['PresentationView']
export type PresentationTheme = PresentationView['theme']

// Monitoring object types a presentation element can bind to. Absent keeps the
// legacy host/service derivation.
export type PresentationObjectType = NonNullable<Daemon['DataElement']['object_type']>

export type ElementLabel = Daemon['ElementLabel']
export type ElementDisplay = Daemon['ElementDisplay']

export type ShapeElement = Daemon['ShapeElement']
export type TextElement = Daemon['TextElement']
export type ImageElement = Daemon['ImageElement']
export type DataElement = Daemon['DataElement']
export type GroupElement = Daemon['GroupElement']

export type PresentationElement = NonNullable<PresentationView['elements']>[number]

/** Which kind of map a view is -- the discriminator every map-type branch tests. */
export type MapViewType = MapView['type']

export type MapView =
  | StaticView
  | WorldmapView
  | RadarView
  | FlowView
  | FolderTreeView
  | PresentationView

// Unsaved server-side foldertree view fields the Settings preview sends so the
// server rebuilds the tree without persisting. Client-side fields (problems_only,
// default_view, expand depth) are mirrored in the map and stay out of this.
export interface FolderTreeOverride {
  rootFolder: string
  showEmptyFolders: boolean
  onlyHardStates: boolean
  sites: string[]
}

// The resolved folder tree of a foldertree map. ``ok_group`` is the one field
// the SPA adds: a synthetic node grouping a folder's healthy hosts into a single
// "N OK" container so problems dominate the treemap. It never crosses the wire,
// but it rides in the same tree the renderer walks.
export type FolderTreeNode = Omit<Daemon['FolderTreeNode'], 'children'> & {
  children: FolderTreeNode[]
  ok_group?: boolean
}

export type FolderTreeNodePatch = Daemon['FolderTreeNodePatch']

export type FolderTreeDelta = Omit<Daemon['FolderTreeDelta'], 'tree'> & {
  tree?: FolderTreeNode | null
}

export type FolderHostService = Daemon['FolderHostService']
export type FolderServiceMatch = Daemon['FolderServiceMatch']
export type FolderServiceSearchResult = Daemon['FolderServiceSearchResult']

// What a monitoring command is sent about, when it is sent about several
// things at once: the leaves of an aggregation, or the nodes an operator picked
// on a flow map. One declaration so a future field (a site id, for federated
// targets) lands in one place.
export interface CommandTarget {
  host: string
  service: string | null
  /** Which site to send it to, where that is known. Federated setups need it. */
  site: string | null
}

export type HostState = 'UP' | 'DOWN' | 'UNREACHABLE' | 'PENDING'
export type ServiceState = 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING'
export type MonitoringState = HostState | ServiceState | 'NO_PERMISSION' | 'NOT_FOUND'

// The map as it is stored and edited: one flat object per element. The daemon
// receives exactly this (the GUI signs it verbatim), so its schema is the model
// — the REST API's grouped shape is a wire format ``api/wire.ts`` translates to.
//
// Two fields are the SPA's own and never stored (``objectToWire`` in api/wire.ts
// is a whitelist): ``site_id``, the host's monitoring site, so commands route
// correctly on topology-driven maps whose objects are not in the state map, and
// ``map_title``, so a link reads as the map it points at rather than as the id
// it stores. A link whose target is gone or invisible carries no title.
export type MapElement = Omit<Daemon['MapElement'], 'type'> & {
  type: ObjectType
  site_id?: string | null
  map_title?: string | null
}

export type ClickAction = Daemon['MapConfig']['click_action']

export type RenderMode = Daemon['MapConfig']['render_mode']

export type MapConfig = Omit<Daemon['MapConfig'], 'objects' | 'view'> & {
  objects: MapElement[]
  view: MapView
}

/**
 * What the legacy ``.cfg`` importer answers: the draft map plus the guesses it
 * had to make. A ``.cfg`` names the backends of the NagVis installation it came
 * from, so connections get remapped onto the ones configured here — every such
 * remap is reported rather than applied silently.
 */
export interface CfgImport {
  map: MapConfig
  warnings: string[]
}

export interface MapRead {
  name: string
  alias: string
  background_image?: string | null
  background_color?: string | null
  icon_size: number | null
  connection_id: string
  view_type: string
  view: MapView
  object_count: number
  rotation_interval: number
  version?: number
  sort_order: number
  click_action: ClickAction
  hide_in_monitor_menu?: boolean
  hover_template?: string | null
  context_template?: string | null
  render_mode?: RenderMode
  default_z?: number
  // Pagetype authorization for this exact instance: built-ins and unauthorized
  // foreign maps are read-only / undeletable. Drive the edit/delete UI off these,
  // not off admin status.
  can_edit?: boolean
  can_delete?: boolean
  // Visuals ownership / sharing (Customize list). ``public``: false = private,
  // true = published to all, or a [scope, names] tuple for contact-groups/sites.
  owner?: string
  is_builtin?: boolean
  public?: MapPublic
}

export type MapPublic = boolean | ['contact_groups' | 'sites', string[]]

/**
 * What the pagetype keeps beside the map: who may see it and whether the
 * Monitor menu links it. Sent whole or not at all — left out, it stays as
 * stored on update.
 */
export interface MapEnvelope {
  public: MapPublic
  hide_in_monitor_menu: boolean
}

export interface MapBulkDeleteFailure {
  name: string
  reason: string
}

export interface MapBulkDeleteResult {
  deleted: string[]
  failed: MapBulkDeleteFailure[]
}

export interface MapBulkEditFailure {
  name: string
  reason: string
}

export interface MapBulkEditResult {
  updated: string[]
  failed: MapBulkEditFailure[]
}

export type ServicesSummary = Daemon['ServicesSummary']

// The daemon types ``state`` as a plain string: it passes Livestatus values
// through, so a value outside the set below is possible and must not fail
// validation there. Consumers that switch on it narrow with a cast, the way the
// foldertree path does.
export type ObjectState = Daemon['ObjectState']

export type PerfometerSegment = Schemas['MapsPerfometerSegment']
export type PerfometerSide = Schemas['MapsPerfometerSide']

// GUI-rendered Perf-O-Meter (the maps_metric_info endpoint). ``rows`` are the
// projected segment stacks exactly as Checkmk's views render them, including
// the theme background filler — ``bg_color`` identifies it so Maps can swap
// in its own remainder style.
export type PerfometerResult = Schemas['MapsPerfometer']

// cmk-shared-typing UnitFormat plus the perfdata->registry scale factor, per raw
// perfdata label; derived from MetricInfoEntry for the value formatters
// (renderMetricValue).
export type MetricUnitSpec = Schemas['MapsMetricUnit'] & { scale: number }

export type MetricUnitMap = Record<string, MetricUnitSpec>

// Display semantics of one raw perfdata label, resolved through the CMK metric
// registry by the maps_metric_info endpoint. Labels without a registry entry are
// omitted from the map — consumers fall back to client-side heuristics for those.
export type MetricInfoEntry = Schemas['MapsMetric']

export type MetricInfoResult = Schemas['MapsMetricInfoResponse']

// One scheduled downtime as the SPA lists it. Not a wire type: the Checkmk REST
// API answers with domain objects, and this is the row projected out of one.
export interface DowntimeEntry {
  id: string
  site_id: string
  host_name: string
  service_description?: string
  author: string
  comment: string
  start_time: string
  end_time: string
  type: 'host' | 'service'
}

export type ServiceNode = Daemon['ServiceNode']
export type TopologyNode = Daemon['TopologyNode']
export type MapStates = Daemon['MapStates']

// The current user, distilled from the Checkmk session ticket.
// Only attributes Checkmk actually provides for the logged-in user are kept; the
// standalone notions (numeric id, active flag, password state, role/permission
// lists, separate cmk_* mirrors) are gone — read everything from Checkmk.
export interface UserRead {
  user_id: string
  is_admin: boolean
  language: string
  can_configure: boolean
  can_create_maps: boolean
  command_permissions: string[]
}

export type GroupMember = Schemas['MapsMember']

export type ConnectionConfig = Daemon['ConnectionListEntry']

// The GUI-owned authoring defaults (Setup -> Global settings), read from the
// INTERNAL REST endpoint. Not editable in the SPA.
export type GlobalSettings = Schemas['MapsAuthoringSettings']
export type TileSource = Schemas['MapsTileSource']

export type MapListView = 'cards' | 'table'

// The knobs the daemon is running on. It sends them with every states payload
// rather than the GUI hydrating them, so a long-lived tab picks up a changed
// cadence on the next tick.
export type DaemonRuntime = Daemon['DaemonRuntime']

export type LogLevel = DaemonRuntime['log_level']

export type ObjectTiming = Daemon['ObjectTiming']

// The ``states`` payload of a stream ``state_update``: like MapStates, but the
// foldertree arrives as a delta rather than the whole tree each tick.
export type StateUpdatePayload = Omit<Daemon['StreamedMapStates'], 'folder_tree_delta'> & {
  folder_tree_delta?: FolderTreeDelta | null
}

export type StateUpdateMessage = Omit<Daemon['StateUpdateMessage'], 'states'> & {
  states: StateUpdatePayload
}

export type ServiceTiming = Daemon['ServiceTiming']
export type TopologyTiming = Daemon['TopologyTiming']
export type TopologyDelta = Daemon['TopologyDelta']
export type TopologyUpdateMessage = Daemon['TopologyUpdateMessage']

// What the stream can deliver.
export type StreamMessage = StateUpdateMessage | TopologyUpdateMessage

export type ImageEntry = Schemas['MapsImage']
export type ImageUsageEntry = Schemas['MapsImageUsage']

export type MetricPoint = Daemon['MetricPoint']

export type MetricGraphGroup = Schemas['MapsGraphGroup']

export interface MetricChoice {
  name: string
  title: string
}

export type MetricHistoryResponse = Daemon['MetricHistoryResponse']

// The raw perfdata source of an object: parsed labels plus the inputs the GUI
// needs to resolve display semantics.
export type PerfMetricsSource = Schemas['MapsPerfMetricsResponse']

export type CommentInfo = Daemon['CommentInfo']
export type DowntimeInfo = Daemon['DowntimeInfo']
export type ObjectDetails = Daemon['ObjectDetails']
