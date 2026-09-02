/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type EventStream, createEventStream } from 'cmk-ui-library/lib/daemon-client/eventStream'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, type ShallowRef, markRaw, ref, shallowRef, triggerRef, watch } from 'vue'

import type { ConnectionsApi } from '@/maps/api/connections'
import type { MapStatesApi, RadarOverride } from '@/maps/api/mapStates'
import type { MonitoringObjectsApi } from '@/maps/api/monitoringObjects'
import type { MapService } from '@/maps/services/MapService'
import type { MapsAuthService } from '@/maps/services/MapsAuthService'
import type {
  AggregationNode,
  DaemonRuntime,
  FolderTreeDelta,
  FolderTreeNode,
  FolderTreeOverride,
  MapConfig,
  MapElement,
  MetricPoint,
  MonitoringState,
  ObjectState,
  StreamMessage,
  TopologyDelta,
  TopologyNode,
  TopologyTiming
} from '@/maps/types/api'
import { resolveStreamUrl } from '@/maps/utils/deploymentBase'
import { parsePerfData } from '@/maps/utils/perf'

// BI integer state -> Maps MonitoringState (mirrors the daemon's BI_INT_TO_STATE
// in cmk.maps.backend.connections.base). BI resolves GUI-side, so the SPA maps.
const BI_STATE: Record<number, MonitoringState> = {
  [-2]: 'UNKNOWN',
  [-1]: 'PENDING',
  0: 'OK',
  1: 'WARNING',
  2: 'CRITICAL',
  3: 'UNKNOWN',
  4: 'UNKNOWN'
}
function biState(n: number): MonitoringState {
  return BI_STATE[n] ?? 'UNKNOWN'
}
// Depth the detail drawer needs for the full leaf list even when the icon is
// collapsed on the canvas.
const AGG_DRAWER_DEPTH = 10
// BI aggregations refresh on their own cadence: they depend on hosts/services
// that may not be on the map (so no SSE tick reflects their change), and a
// map of only aggregation objects gets no SSE traffic at all. A dedicated
// interval keeps them live regardless of the daemon stream. The cadence follows
// the global "State refresh interval" (the same knob the daemon streams state
// at), falling back to this when the setting hasn't loaded yet.
const AGG_POLL_FALLBACK_S = 5

const HISTORY_MAX = 10080 // up to 7d at 1min resolution

const NOTIFICATIONS_STORAGE_KEY = 'maps_notifications'

const BAD_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN'])
const SEVERITY: Record<string, number> = {
  OK: 0,
  UP: 0,
  PENDING: 0,
  WARNING: 1,
  UNKNOWN: 1,
  CRITICAL: 2,
  UNREACHABLE: 2,
  DOWN: 3
}

// Fire a browser notification when `name` worsens into a bad state. Shared by
// the flat-states path and the foldertree snapshot diff so the policy lives once.
function maybeNotify(name: string, state: string, prevState: string | undefined) {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') {
    return
  }
  const prevSev = SEVERITY[prevState ?? 'OK'] ?? 0
  const newSev = SEVERITY[state] ?? 0
  if (newSev <= prevSev || !BAD_STATES.has(state)) {
    return
  }
  new Notification(`Maps: ${state}`, { body: name, tag: name })
}

function notifyStateChange(obj: ObjectState, prev: ObjectState | undefined) {
  maybeNotify(obj.object_id, obj.state, prev?.state)
}

function collectFolderHostStates(node: FolderTreeNode, out: Map<string, string>) {
  if (node.kind === 'host') {
    out.set(node.title, node.state)
    return
  }
  for (const c of node.children) {
    collectFolderHostStates(c, out)
  }
}

// Index every node by its (unique) path so folder-tree deltas can patch in place.
function indexFolderTree(node: FolderTreeNode, out: Map<string, FolderTreeNode>) {
  out.set(node.path, node)
  for (const c of node.children) {
    indexFolderTree(c, out)
  }
}

// Foldertree maps ship no flat states list, so host-state notifications are
// derived by diffing successive tree snapshots. Returns the new snapshot to
// store; a null `prev` only primes (else every bad host would alert on load).
function diffNotifyFolderTree(
  tree: FolderTreeNode | null,
  prev: Map<string, string> | null
): Map<string, string> | null {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted' || !tree) {
    return null
  }
  const current = new Map<string, string>()
  collectFolderHostStates(tree, current)
  if (prev !== null) {
    for (const [host, state] of current) {
      maybeNotify(host, state, prev.get(host))
    }
  }
  return current
}

/** How often the polling fallback refetches while the stream is unavailable. */
const POLL_INTERVAL_MS = 15_000
/** How often to test whether the stream has become reachable again. */
const STREAM_REPROBE_INTERVAL_MS = 60_000
/**
 * How long a hidden tab keeps its stream. An open stream holds one of the few
 * connections a browser allows per host and a site Apache worker, so a tab left
 * in the background gives both back. The delay only spares a glance at another
 * tab the reconnect; the daemon sends a full state to every stream that joins.
 */
const HIDDEN_STREAM_GRACE_MS = 5_000

/**
 * The live state of the open map.
 *
 * The daemon pushes state and topology over one event stream and the service
 * applies it: full ticks replace, deltas patch. The connection itself — opening,
 * reconnecting, and falling back to polling behind a proxy that will not pass
 * ``text/event-stream`` — belongs to the shared stream client, so what is left
 * here is only what the frames mean.
 *
 * BI aggregations are the exception: they are resolved GUI-side and refreshed on
 * their own interval, because they depend on hosts and services that need not be
 * on the map, so no tick of the map's own stream would reflect their change.
 */
export class MapStatesService {
  public readonly states: Ref<Record<string, ObjectState>> = ref({})
  public readonly metricValues: Ref<Record<string, Record<string, MetricPoint[]>>> = ref({})
  public readonly metricTitles: Ref<Record<string, Record<string, string>>> = ref({})
  public readonly connected: Ref<boolean> = ref(false)
  /**
   * Distributed monitoring: federation sites that stopped answering. Foldertree
   * leaves from these sites freeze on their last known state.
   */
  public readonly deadSites: Ref<string[]> = ref([])
  public readonly lastUpdate: Ref<number | null> = ref(null)
  public readonly initialLoad: Ref<boolean> = ref(false)
  /**
   * Why state could not be read, null while it can be. A map whose content *is*
   * the snapshot -- a radar map -- has nothing to fall back on and would
   * otherwise sit on a spinner that never stops, so it shows this instead.
   */
  public readonly loadError: Ref<string | null> = ref(null)
  public readonly topology: Ref<TopologyNode[]> = ref([])
  public readonly topologyReady: Ref<boolean> = ref(false)
  /**
   * Bumped on every applied topology timing patch. A consumer reading a node's
   * timing off a captured reference (the flow map's drawer) watches this to
   * re-derive; the in-place field write alone does not always trigger it.
   */
  public readonly topologyTimingVersion: Ref<number> = ref(0)
  /**
   * The resolved tree of a foldertree map, null for every other type.
   *
   * Not deep-reactive: at 100k+ nodes that alone costs more than the render. A
   * full tick replaces it wholesale, a delta patches nodes in place through the
   * path index and notifies with ``triggerRef``.
   */
  public readonly folderTree: ShallowRef<FolderTreeNode | null> = shallowRef(null)
  /**
   * Nodes patched in place are invisible to Vue, and ``triggerRef`` is swallowed
   * by a ``computed`` that returns the same reference. Consumers read this
   * counter to re-derive.
   */
  public readonly folderTreeVersion: Ref<number> = ref(0)
  /** False once the stream turned out to be unreachable and polling took over. */
  public readonly streamAvailable: Ref<boolean> = ref(true)
  public readonly notificationsEnabled: Ref<boolean> = ref(
    typeof Notification !== 'undefined' &&
      Notification.permission === 'granted' &&
      localStorage.getItem(NOTIFICATIONS_STORAGE_KEY) === '1'
  )
  /**
   * A radar filter the settings preview is editing. While set, the next fetch
   * carries it instead of the stored one.
   */
  public readonly radarOverride: Ref<RadarOverride | null> = ref(null)
  /**
   * The same for a foldertree's server-side view fields. While set, stream deltas
   * are ignored, because they are built from the stored config and would clobber
   * the preview.
   */
  public readonly folderOverride: Ref<FolderTreeOverride | null> = ref(null)
  /** The knobs the daemon is running on, as it reported them with the last tick. */
  public readonly runtime: Ref<DaemonRuntime | null> = ref(null)

  private stream: EventStream | null = null
  private currentMap: string | null = null
  /**
   * The map a connect is in flight for. The "already open" guard below only
   * catches a reconnect once the stream is up; this catches an overlapping
   * connect before that (a view effect firing twice on mount), which otherwise
   * tore down and re-registered on every load.
   */
  private connectingMap: string | null = null
  private folderTreeIndex = new Map<string, FolderTreeNode>()
  /** Previous foldertree host states, for deriving notifications. */
  private prevFolderHostStates: Map<string, string> | null = null
  private aggTimer: ReturnType<typeof setInterval> | null = null
  private postCommandTimer: ReturnType<typeof setTimeout> | null = null
  private aggInFlight = false
  private hiddenTimer: ReturnType<typeof setTimeout> | null = null
  /** True while the tab is hidden and the stream and aggregation poll are closed. */
  private paused = false

  public constructor(
    private readonly api: Pick<MapStatesApi, 'register' | 'registerEdit' | 'fetchStates'>,
    private readonly connectionsApi: Pick<ConnectionsApi, 'fetchMetricHistory'>,
    private readonly objectsApi: Pick<
      MonitoringObjectsApi,
      'fetchAggregationStates' | 'fetchAggregationTree'
    >,
    private readonly auth: Pick<MapsAuthService, 'setStreamMap' | 'streamToken'>,
    private readonly maps: Pick<MapService, 'currentMap'>
  ) {
    // The ticket is re-minted every few minutes and the stream token rotates
    // with it. A long-open map would keep the stale one in its URL until the
    // daemon rejected it, so re-point the stream as soon as a new one arrives.
    // The polling fallback reads its credential per request, so only an open
    // stream needs this.
    watch(this.auth.streamToken, (token, previous) => {
      if (token && previous && token !== previous) {
        this.reconnectStream()
      }
    })
  }

  public getState(objectId: string): ObjectState | undefined {
    return this.states.value[objectId]
  }

  /**
   * Binds to a map: scopes the ticket to it, hands the daemon the signed config,
   * loads the first states and opens the stream.
   */
  public async connectToMap(
    mapName: string,
    signed?: { config_b64: string; sig: string }
  ): Promise<void> {
    const { _t } = usei18n()
    if (this.connectingMap === mapName) {
      return
    }
    if (this.currentMap === mapName && this.stream) {
      return
    }
    this.connectingMap = mapName
    try {
      this.disconnect()
      // Re-scope the ticket before anything talks to the daemon, so registering
      // and the stream URL carry a map-scoped token whose baked-in owner lets the
      // daemon share one broadcast loop across the map's viewers.
      await this.auth.setStreamMap(mapName)
      this.currentMap = mapName
      this.initialLoad.value = true
      try {
        if (signed) {
          await this.api.register(signed)
        }
        await this.refresh()
        // Resolve aggregations now that the map's objects are loaded, then keep
        // them live on their own interval.
        void this.refreshAggregations()
        this.startAggregationTimer()
      } finally {
        this.initialLoad.value = false
      }
      await this.openStream(mapName)
    } catch (e: unknown) {
      // Also for a daemon that never answered: the caller reports it, but a map
      // that got no states needs the reason on screen, not only in a toast.
      this.loadError.value = e instanceof Error ? e.message : _t('Live connection failed')
      throw e
    } finally {
      this.connectingMap = null
    }
  }

  /**
   * Re-pushes a locally edited config and refetches.
   *
   * The daemon caches the map it was handed at connect time, so an edit that
   * changes the resolvable object set would otherwise show no state until a full
   * reload. Idempotent and cheap (in-memory on the daemon).
   */
  public async reregister(map: MapConfig): Promise<void> {
    if (!this.currentMap || map.name !== this.currentMap) {
      return
    }
    await this.api.registerEdit(map)
    await this.refresh()
    // The edit may have added or removed aggregation objects; resolve now rather
    // than waiting for the next interval tick.
    void this.refreshAggregations()
  }

  public dispose(): void {
    this.disconnect()
  }

  public disconnect(): void {
    document.removeEventListener('visibilitychange', this.onVisibilityChange)
    this.clearHiddenTimer()
    this.paused = false
    this.stream?.disconnect()
    this.stream = null
    this.stopAggregationTimer()
    if (this.postCommandTimer) {
      clearTimeout(this.postCommandTimer)
      this.postCommandTimer = null
    }
    this.connected.value = false
    this.initialLoad.value = false
    this.loadError.value = null
    this.states.value = {}
    this.metricValues.value = {}
    this.metricTitles.value = {}
    this.topology.value = []
    this.topologyReady.value = false
    this.folderTree.value = null
    this.folderTreeIndex = new Map()
    this.prevFolderHostStates = null
    this.folderOverride.value = null
    // Reset so the next map attempts the stream fresh instead of inheriting a
    // sticky fallback from a map that happened to be unreachable.
    this.streamAvailable.value = true
    this.currentMap = null
  }

  /** Refetches the map's states now. */
  public async refresh(): Promise<void> {
    const { _t } = usei18n()
    if (!this.currentMap) {
      return
    }
    const mapAtStart = this.currentMap
    try {
      const data = await this.api.fetchStates(
        mapAtStart,
        this.radarOverride.value,
        this.folderOverride.value
      )
      if (this.currentMap !== mapAtStart) {
        return
      }
      const newStates: Record<string, ObjectState> = {}
      const ts = Date.now() / 1000
      for (const s of data.states) {
        if (this.notificationsEnabled.value) {
          notifyStateChange(s, this.states.value[s.object_id])
        }
        newStates[s.object_id] = s
        if (s.perf_data) {
          this.recordMetricValues(s.object_id, s.perf_data, ts)
        }
      }
      for (const id of Object.keys(this.states.value)) {
        // Aggregation entries are owned by the aggregation poll, not by the
        // daemon, so they are never in `newStates` and must not be dropped.
        if (!newStates[id] && this.states.value[id]?.type !== 'aggregation') {
          delete this.states.value[id]
        }
      }
      Object.assign(this.states.value, newStates)
      this.lastUpdate.value = ts
      this.connected.value = data.connection_ok
      this.deadSites.value = data.dead_sites
      this.runtime.value = data.runtime
      this.setFolderTree(data.folder_tree ?? null)
      if (this.notificationsEnabled.value) {
        this.prevFolderHostStates = diffNotifyFolderTree(
          this.folderTree.value,
          this.prevFolderHostStates
        )
      }
      this.loadError.value = null
    } catch (e: unknown) {
      this.connected.value = false
      this.loadError.value = e instanceof Error ? e.message : _t('Failed to load states')
    }
  }

  /** Refetches with the loading indicator, for an explicit user refresh. */
  public async refreshWithIndicator(): Promise<void> {
    this.initialLoad.value = true
    try {
      await this.refresh()
    } finally {
      this.initialLoad.value = false
    }
  }

  /**
   * Refetches after a command. Twice, because the monitoring core applies a
   * command asynchronously and the first read can still show the old state.
   */
  public refreshAfterCommand(): void {
    void this.refresh()
    if (this.postCommandTimer) {
      clearTimeout(this.postCommandTimer)
    }
    this.postCommandTimer = setTimeout(() => {
      this.postCommandTimer = null
      void this.refresh()
    }, 1500)
  }

  public setRadarOverride(filter: string | null, filterValue?: string): void {
    this.radarOverride.value =
      filter && typeof filterValue === 'string' ? { filter, filterValue } : null
    void this.refresh()
  }

  /**
   * Refetches only when a server-side field actually changed: the client-side
   * toggles re-post the whole patch, and a full tree rebuild costs seconds on a
   * site with 100k hosts.
   */
  public setFolderTreeOverride(override: FolderTreeOverride | null): void {
    if (JSON.stringify(override) === JSON.stringify(this.folderOverride.value)) {
      return
    }
    this.folderOverride.value = override
    void this.refresh()
  }

  public async toggleNotifications(): Promise<void> {
    if (typeof Notification === 'undefined') {
      return
    }
    if (this.notificationsEnabled.value) {
      this.notificationsEnabled.value = false
      localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, '0')
      return
    }
    if (Notification.permission === 'denied') {
      return
    }
    if (Notification.permission !== 'granted') {
      const result = await Notification.requestPermission()
      if (result !== 'granted') {
        return
      }
    }
    this.notificationsEnabled.value = true
    localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, '1')
  }

  /** Seeds an object's metric history from the backend, for a chart opened cold. */
  public async prefillMetricHistory(
    objectId: string,
    connectionId: string,
    host: string,
    service: string | null,
    timeWindowMinutes: number
  ): Promise<void> {
    try {
      const data = await this.connectionsApi.fetchMetricHistory(
        connectionId,
        host,
        service,
        timeWindowMinutes
      )
      if (!Object.keys(data.series).length) {
        return
      }
      if (Object.keys(data.titles).length) {
        this.metricTitles.value[objectId] = { ...data.titles }
      }
      const values: Record<string, MetricPoint[]> = { ...(this.metricValues.value[objectId] ?? {}) }
      for (const [label, points] of Object.entries(data.series)) {
        const existing = values[label] ?? []
        const existingTs = new Set(existing.map((p) => p.ts))
        values[label] = [...points.filter((p) => !existingTs.has(p.ts)), ...existing]
          .sort((a, b) => a.ts - b.ts)
          .slice(-HISTORY_MAX)
      }
      this.metricValues.value[objectId] = values
    } catch {
      // A backend without metric history (plain Nagios) is not an error here.
    }
  }

  public clearMetricValues(objectId: string): void {
    this.metricValues.value[objectId] = {}
  }

  /**
   * Re-points the open stream at a freshly minted credential.
   *
   * The stream token rotates with the ticket, and a long-open map would otherwise
   * keep the stale one in its URL until the daemon rejects it.
   */
  public reconnectStream(): void {
    if (this.paused) {
      return
    }
    void this.stream?.reconnect()
  }

  private async openStream(mapName: string): Promise<void> {
    this.stream = createEventStream({
      url: () => {
        const token = this.auth.streamToken.value
        if (!token) {
          // No stream credential (a transient re-mint failure kept the API
          // ticket): let the caller's fallback carry the map until one arrives.
          throw new Error('No Maps stream token available')
        }
        return resolveStreamUrl(mapName, token)
      },
      onMessage: (payload) => this.applyStreamMessage(payload as StreamMessage),
      poll: {
        fetch: () => this.refresh(),
        intervalMs: POLL_INTERVAL_MS,
        reprobeIntervalMs: STREAM_REPROBE_INTERVAL_MS
      },
      onFallback: () => {
        this.streamAvailable.value = false
      },
      onRecovered: () => {
        this.streamAvailable.value = true
      }
    })
    document.addEventListener('visibilitychange', this.onVisibilityChange)
    // A map opened in a background tab has its first states from the fetch and
    // opens the stream only once it is looked at.
    if (document.hidden) {
      this.pause()
      return
    }
    await this.stream.connect()
  }

  private readonly onVisibilityChange = (): void => {
    if (document.hidden) {
      this.schedulePause()
      return
    }
    this.clearHiddenTimer()
    if (this.paused) {
      this.resume()
    }
  }

  private schedulePause(): void {
    if (this.hiddenTimer || this.paused) {
      return
    }
    this.hiddenTimer = setTimeout(() => {
      this.hiddenTimer = null
      this.pause()
    }, HIDDEN_STREAM_GRACE_MS)
  }

  private clearHiddenTimer(): void {
    if (this.hiddenTimer) {
      clearTimeout(this.hiddenTimer)
      this.hiddenTimer = null
    }
  }

  private pause(): void {
    this.paused = true
    this.stream?.disconnect()
    this.stopAggregationTimer()
  }

  private resume(): void {
    this.paused = false
    // A fresh connect tries the stream first even if it had fallen back to
    // polling; a stream that still cannot open reports the fallback again.
    this.streamAvailable.value = true
    void this.stream?.connect()
    void this.refreshAggregations()
    this.startAggregationTimer()
  }

  private applyStreamMessage(msg: StreamMessage): void {
    if (msg.type === 'state_update') {
      this.applyStateUpdate(msg)
    } else {
      this.applyTopologyDelta(msg.delta)
      this.topologyReady.value = true
      this.lastUpdate.value = msg.delta.generated_at
    }
  }

  private applyStateUpdate(msg: Extract<StreamMessage, { type: 'state_update' }>): void {
    for (const s of msg.states.states) {
      if (this.notificationsEnabled.value) {
        notifyStateChange(s, this.states.value[s.object_id])
      }
      this.states.value[s.object_id] = s
      if (s.perf_data) {
        this.recordMetricValues(s.object_id, s.perf_data, msg.states.generated_at)
      }
    }
    if (msg.full) {
      const incoming = new Set(msg.states.states.map((s) => s.object_id))
      for (const id of Object.keys(this.states.value)) {
        // Keep the GUI-resolved aggregation entries across a full resend.
        if (!incoming.has(id) && this.states.value[id]?.type !== 'aggregation') {
          delete this.states.value[id]
        }
      }
    } else {
      for (const id of msg.removed_ids) {
        delete this.states.value[id]
      }
    }
    // Keeps next-check and overdue live without resending full state per recheck.
    for (const tm of msg.timing) {
      const existing = this.states.value[tm.object_id]
      if (existing) {
        existing.last_check = tm.last_check ?? null
        existing.next_check = tm.next_check ?? null
        existing.current_attempt = tm.current_attempt
      }
    }
    this.lastUpdate.value = msg.states.generated_at
    this.connected.value = msg.states.connection_ok
    this.deadSites.value = msg.states.dead_sites
    this.runtime.value = msg.states.runtime
    // A delta built from the stored config would overwrite a preview override.
    if (!this.folderOverride.value) {
      this.applyFolderTreeDelta(msg.states.folder_tree_delta)
    }
    if (this.notificationsEnabled.value) {
      this.prevFolderHostStates = diffNotifyFolderTree(
        this.folderTree.value,
        this.prevFolderHostStates
      )
    }
  }

  /** Replaces the whole tree (first load or a full tick) and rebuilds the index. */
  private setFolderTree(tree: FolderTreeNode | null): void {
    this.folderTree.value = tree ? markRaw(tree) : null
    this.folderTreeIndex = new Map()
    if (tree) {
      indexFolderTree(tree, this.folderTreeIndex)
    }
    this.folderTreeVersion.value++
  }

  private applyFolderTreeDelta(delta: FolderTreeDelta | null | undefined): void {
    if (!delta) {
      return
    }
    if (delta.full) {
      this.setFolderTree(delta.tree ?? null)
      return
    }
    for (const patch of delta.changed) {
      const node = this.folderTreeIndex.get(patch.path)
      if (!node) {
        continue
      }
      node.title = patch.title
      node.site_id = patch.site_id ?? null
      node.state = patch.state
      node.is_empty = patch.is_empty
      node.host_count = patch.host_count
      node.problem_count = patch.problem_count
      node.severity_counts = patch.severity_counts
      node.output = patch.output
      node.acknowledged = patch.acknowledged
      node.in_downtime = patch.in_downtime
      node.is_flapping = patch.is_flapping
      node.stale = patch.stale
      node.last_state_change = patch.last_state_change ?? null
      node.services_summary = patch.services_summary ?? null
      if (patch.children_order) {
        const byPath = new Map(node.children.map((c) => [c.path, c]))
        node.children = patch.children_order
          .map((path) => byPath.get(path))
          .filter((c): c is FolderTreeNode => c !== undefined)
      }
    }
    triggerRef(this.folderTree)
    this.folderTreeVersion.value++
  }

  private applyTopologyDelta(delta: TopologyDelta): void {
    if (delta.full) {
      this.topology.value = [...delta.added]
      this.applyTopologyTiming(delta.timing)
      return
    }
    // Only rebuild the array — which makes the flow map re-derive its d3 nodes —
    // when the structure actually changed. A timing-only tick patches in place
    // below: no node rebuild, no force-simulation restart, just the open drawer
    // reading the new next-check.
    if (delta.removed.length || delta.changed.length || delta.added.length) {
      const removed = new Set(delta.removed)
      const updated = new Map(delta.changed.map((n) => [n.name, n] as const))
      this.topology.value = this.topology.value
        .filter((n) => !removed.has(n.name))
        .map((n) => updated.get(n.name) ?? n)
        .concat(delta.added)
    }
    this.applyTopologyTiming(delta.timing)
  }

  /**
   * Patches check timing onto existing topology nodes in place, which keeps a
   * consumer reading ``.next_check`` live without replacing the array.
   */
  private applyTopologyTiming(timing: TopologyTiming[]): void {
    if (!timing.length) {
      return
    }
    this.topologyTimingVersion.value++
    const byName = new Map(this.topology.value.map((n) => [n.name, n] as const))
    for (const tm of timing) {
      const node = byName.get(tm.name)
      if (!node) {
        continue
      }
      node.last_check = tm.last_check ?? null
      node.next_check = tm.next_check ?? null
      node.current_attempt = tm.current_attempt
      if (tm.services.length && node.services.length) {
        const byService = new Map(node.services.map((s) => [s.name, s] as const))
        for (const st of tm.services) {
          const service = byService.get(st.name)
          if (service) {
            service.last_check = st.last_check ?? null
            service.next_check = st.next_check ?? null
          }
        }
      }
    }
  }

  private startAggregationTimer(): void {
    if (this.aggTimer) {
      return
    }
    const seconds = this.runtime.value?.state_refresh_interval || AGG_POLL_FALLBACK_S
    this.aggTimer = setInterval(() => void this.refreshAggregations(), Math.max(1, seconds) * 1000)
  }

  private stopAggregationTimer(): void {
    if (this.aggTimer) {
      clearInterval(this.aggTimer)
      this.aggTimer = null
    }
  }

  /**
   * Resolves the map's BI aggregation objects GUI-side and merges them into the
   * same state map, keyed by object id. This owns those entries — the daemon does
   * not stream them.
   */
  private async refreshAggregations(): Promise<void> {
    if (this.aggInFlight) {
      return
    }
    const map = this.maps.currentMap.value
    const aggObjects = (map?.objects ?? []).filter(
      (o): o is MapElement & { aggregation_id: string } =>
        o.type === 'aggregation' &&
        typeof o.aggregation_id === 'string' &&
        o.aggregation_id.length > 0
    )
    if (!aggObjects.length) {
      return
    }
    this.aggInFlight = true
    try {
      const ids = [...new Set(aggObjects.map((o) => o.aggregation_id))]
      const raw = await this.objectsApi.fetchAggregationStates(ids)
      // An expanded icon renders its subtree on the canvas, so those (and only
      // those) also need the tree; the drawer fetches its own when it opens.
      const treeByAgg = new Map<string, AggregationNode | null>()
      await Promise.all(
        [
          ...new Set(
            aggObjects.filter((o) => (o.expand_depth ?? 0) > 0).map((o) => o.aggregation_id)
          )
        ].map(async (aggId) => {
          const { tree } = await this.objectsApi.fetchAggregationTree(aggId, AGG_DRAWER_DEPTH)
          treeByAgg.set(aggId, tree)
        })
      )
      for (const o of aggObjects) {
        const state = raw[o.aggregation_id]
        this.states.value[o.id] = state
          ? aggregationState(o.id, {
              state: biState(state.state),
              output: state.output,
              acknowledged: state.acknowledged,
              in_downtime: state.in_downtime,
              stale: false,
              tree: treeByAgg.get(o.aggregation_id) ?? null
            })
          : aggregationState(o.id, { state: 'PENDING', stale: true })
      }
    } catch {
      // Leave existing entries in place on a transient failure; the next tick
      // retries. The daemon stream's own health is tracked by `connected`.
    } finally {
      this.aggInFlight = false
    }
  }

  private recordMetricValues(objectId: string, perfData: string, ts: number): void {
    const metrics = parsePerfData(perfData)
    if (metrics.length === 0) {
      return
    }
    const values = this.metricValues.value[objectId] ?? {}
    for (const m of metrics) {
      const series = values[m.label] ?? []
      series.push({ ts, value: m.value, unit: m.unit })
      values[m.label] = series.length > HISTORY_MAX ? series.slice(-HISTORY_MAX) : series
    }
    this.metricValues.value[objectId] = values
  }
}

/**
 * A state entry for a BI aggregation. Spelled out because these are built here
 * rather than received, and the daemon's model requires every field.
 */
function aggregationState(
  objectId: string,
  fields: Partial<ObjectState> & { state: MonitoringState }
): ObjectState {
  return {
    object_id: objectId,
    type: 'aggregation',
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
