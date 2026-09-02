/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { computed, ref } from 'vue'

import type { ConnectionsApi } from '@/maps/api/connections'
import type { MapStatesApi } from '@/maps/api/mapStates'
import type { MonitoringObjectsApi } from '@/maps/api/monitoringObjects'
import { MapStatesService } from '@/maps/services/MapStatesService'
import type { MapConfig, MapStates } from '@/maps/types/api'

import { aMap, anObject } from '../support/fixtures'

// What the connection itself does — opening, falling back to polling, healing —
// belongs to the shared stream client and is covered there. What is maps' own is
// what the frames mean: how a tick is merged, how a folder-tree delta is applied,
// and which entries the daemon does not own.

/** Minimal EventSource stand-in that lets a test drive the stream. */
class FakeEventSource {
  static instances: FakeEventSource[] = []
  static readonly OPEN = 1
  static readonly CLOSED = 2
  onopen: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  readyState = 0
  closed = false
  constructor(public url: string) {
    FakeEventSource.instances.push(this)
  }
  close() {
    this.closed = true
    this.readyState = 2
  }
}

const emptyStates: MapStates = {
  map_name: 'b',
  states: [],
  generated_at: 1,
  connection_ok: true,
  dead_sites: [],
  folder_tree: null,
  runtime: { log_level: 'INFO', state_refresh_interval: 5 }
}

// Every service is torn down after its test: an undisconnected one keeps its
// visibility listener and would answer another test's tab switch.
const services: MapStatesService[] = []
afterEach(() => {
  for (const service of services.splice(0)) {
    service.disconnect()
  }
})

function newService(
  map: MapConfig | null = null,
  objectOverrides: Partial<
    Pick<MonitoringObjectsApi, 'fetchAggregationStates' | 'fetchAggregationTree'>
  > = {},
  statesOverrides: Partial<Pick<MapStatesApi, 'register' | 'fetchStates'>> = {}
): MapStatesService {
  const statesApi: Pick<MapStatesApi, 'register' | 'registerEdit' | 'fetchStates'> = {
    register: vi.fn().mockResolvedValue(undefined),
    registerEdit: vi.fn().mockResolvedValue(undefined),
    fetchStates: vi.fn().mockResolvedValue(emptyStates),
    ...statesOverrides
  }
  const connections: Pick<ConnectionsApi, 'fetchMetricHistory'> = {
    fetchMetricHistory: vi.fn().mockResolvedValue({ series: {}, titles: {} })
  }
  const objects: Pick<MonitoringObjectsApi, 'fetchAggregationStates' | 'fetchAggregationTree'> = {
    fetchAggregationStates: vi.fn().mockResolvedValue({}),
    fetchAggregationTree: vi.fn().mockResolvedValue({ tree: null, connection_ok: true }),
    ...objectOverrides
  }
  const auth = {
    setStreamMap: vi.fn().mockResolvedValue(undefined),
    streamToken: computed(() => 'maps-stream-token' as string | null)
  }
  const service = new MapStatesService(statesApi, connections, objects, auth, {
    currentMap: ref(map)
  })
  services.push(service)
  return service
}

describe('MapStatesService — folder-tree delta apply', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  const host = (path: string, state: string) => ({
    path,
    title: path.split('/').pop(),
    kind: 'host',
    state,
    is_empty: false,
    folder_id: '',
    host_count: 1,
    problem_count: state === 'UP' ? 0 : 1,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    is_flapping: false,
    last_state_change: null,
    site_id: null,
    children: []
  })
  const folder = (children: ReturnType<typeof host>[], state = 'OK', problem = 0) => ({
    path: 'f',
    title: 'F',
    kind: 'folder',
    state,
    is_empty: false,
    folder_id: '',
    host_count: children.length,
    problem_count: problem,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    site_id: null,
    children
  })
  const send = (es: FakeEventSource, folderTreeDelta: unknown) =>
    es.onmessage?.({
      data: JSON.stringify({
        type: 'state_update',
        map: 'b',
        full: false,
        removed_ids: [],
        timing: [],
        states: {
          map_name: 'b',
          states: [],
          generated_at: 1,
          connection_ok: true,
          folder_tree_delta: folderTreeDelta
        }
      })
    } as MessageEvent)

  it('applies a full delta then patches changed nodes in place', async () => {
    const store = newService()
    await store.connectToMap('b')
    const es = FakeEventSource.instances[0]!
    es.onopen?.()

    send(es, {
      full: true,
      tree: folder([host('f/h1', 'UP'), host('f/h2', 'UP')]),
      changed: []
    })
    expect(store.folderTree.value?.host_count).toBe(2)
    expect(store.folderTree.value?.state).toBe('OK')

    // markRaw nodes patched in place are invisible to Vue; the version bump is
    // the only signal consumers (rows, treemap) re-derive from. Assert it ticks
    // so a state change shows without an expand/collapse forcing a re-render.
    const revBefore = store.folderTreeVersion.value
    send(es, {
      full: false,
      changed: [
        { ...host('f/h1', 'DOWN'), problem_count: 1 },
        {
          path: 'f',
          title: 'Renamed',
          state: 'CRITICAL',
          is_empty: false,
          host_count: 2,
          problem_count: 1,
          severity_counts: { DOWN: 1 },
          output: '',
          acknowledged: false,
          in_downtime: false,
          is_flapping: false
        }
      ]
    })
    expect(store.folderTreeVersion.value).toBeGreaterThan(revBefore)
    expect(store.folderTree.value?.children.find((c) => c.path === 'f/h1')?.state).toBe('DOWN')
    expect(store.folderTree.value?.state).toBe('CRITICAL')
    expect(store.folderTree.value?.title).toBe('Renamed') // title patch applied (folder rename)
    expect(store.folderTree.value?.severity_counts).toEqual({ DOWN: 1 })
    expect(store.folderTree.value?.children.find((c) => c.path === 'f/h2')?.state).toBe('UP')
  })

  it('reorders children when a delta carries children_order', async () => {
    const store = newService()
    await store.connectToMap('b')
    const es = FakeEventSource.instances[0]!
    es.onopen?.()
    send(es, {
      full: true,
      tree: folder([host('f/h1', 'UP'), host('f/h2', 'UP')]),
      changed: []
    })
    expect(store.folderTree.value?.children.map((c) => c.path)).toEqual(['f/h1', 'f/h2'])

    send(es, {
      full: false,
      changed: [
        {
          path: 'f',
          title: 'F',
          state: 'CRITICAL',
          is_empty: false,
          host_count: 2,
          problem_count: 1,
          severity_counts: {},
          output: '',
          acknowledged: false,
          in_downtime: false,
          is_flapping: false,
          children_order: ['f/h2', 'f/h1']
        }
      ]
    })
    expect(store.folderTree.value?.children.map((c) => c.path)).toEqual(['f/h2', 'f/h1'])
  })
})

describe('MapStatesService — stream credential', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('passes the reduced-scope stream token as the SSE token query parameter', async () => {
    const store = newService()
    await store.connectToMap('b')
    const es = FakeEventSource.instances[0]!
    // The SSE URL must carry the dedicated stream token, never the full API ticket.
    expect(es.url).toContain('token=maps-stream-token')
    expect(es.url).not.toContain('token=maps-ticket')
  })
})

describe('MapStatesService — BI aggregations resolve GUI-side', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('merges the resolved state and tree, and keeps them across a full resend', async () => {
    const map = aMap({
      objects: [
        anObject({ id: 'agg1', type: 'aggregation', aggregation_id: 'Host x', expand_depth: 2 })
      ]
    })
    const objects = {
      fetchAggregationStates: vi.fn().mockResolvedValue({
        'Host x': { state: 2, output: 'crit', acknowledged: false, in_downtime: false }
      }),
      fetchAggregationTree: vi.fn().mockResolvedValue({
        tree: { name: 'Host x', node_type: 'bi_aggregator', state: 2, children: [] },
        connection_ok: true
      })
    }
    const store = newService(map, objects)

    await store.connectToMap('map1')
    // The resolve is fire-and-forget; wait for the entry it produces.
    await vi.waitFor(() => expect(store.getState('agg1')).toBeDefined())

    const state = store.getState('agg1')
    expect(state?.type).toBe('aggregation')
    expect(state?.state).toBe('CRITICAL') // BI integer 2
    expect(state?.output).toBe('crit')
    expect(state?.tree?.name).toBe('Host x')

    // A full tick that omits the entry must not delete it: the daemon does not
    // stream aggregations, so it cannot be authoritative about them.
    FakeEventSource.instances[0]!.onmessage?.({
      data: JSON.stringify({
        type: 'state_update',
        map: 'map1',
        full: true,
        removed_ids: [],
        timing: [],
        states: { ...emptyStates, map_name: 'map1' }
      })
    } as MessageEvent)

    expect(store.getState('agg1')?.state).toBe('CRITICAL')
    store.disconnect()
  })

  it('resolves nothing when the map carries no aggregation', async () => {
    const objects = {
      fetchAggregationStates: vi.fn().mockResolvedValue({}),
      fetchAggregationTree: vi.fn().mockResolvedValue({ tree: null, connection_ok: true })
    }
    const map = aMap({ objects: [anObject({ id: 'h1', type: 'host', host_name: 'x' })] })
    const store = newService(map, objects)

    await store.connectToMap('map1')
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(objects.fetchAggregationStates).not.toHaveBeenCalled()
    store.disconnect()
  })
})

// A map whose content *is* the snapshot has nothing to fall back on, so why the
// snapshot is missing has to be readable rather than only logged.
describe('MapStatesService — why state is missing', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('records why a state fetch failed', async () => {
    const store = newService(
      null,
      {},
      { fetchStates: vi.fn().mockRejectedValue(new Error('Livestatus unreachable')) }
    )

    await store.connectToMap('b')

    expect(store.lastUpdate.value).toBeNull()
    expect(store.loadError.value).toBe('Livestatus unreachable')
  })

  it('records a daemon that no fetch ever got past', async () => {
    const store = newService(
      null,
      {},
      { register: vi.fn().mockRejectedValue(new Error('Maps daemon unreachable')) }
    )

    await expect(store.connectToMap('b', { config_b64: 'x', sig: 'y' })).rejects.toThrow()

    expect(store.loadError.value).toBe('Maps daemon unreachable')
  })

  it('clears the reason once a fetch comes back', async () => {
    const fetchStates = vi
      .fn()
      .mockRejectedValueOnce(new Error('Livestatus unreachable'))
      .mockResolvedValue(emptyStates)
    const store = newService(null, {}, { fetchStates })
    await store.connectToMap('b')

    await store.refresh()

    expect(store.loadError.value).toBeNull()
  })
})

// A background tab gives its stream back, so a user with many Maps tabs does not
// exhaust the browser's connections to the site.
describe('MapStatesService — hidden tab', () => {
  let hidden = false
  const setHidden = (value: boolean) => {
    hidden = value
    document.dispatchEvent(new Event('visibilitychange'))
  }

  beforeEach(() => {
    vi.useFakeTimers()
    hidden = false
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
    vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('closes the stream once the tab stays hidden and reopens it on return', async () => {
    const store = newService()
    await store.connectToMap('b')
    const first = FakeEventSource.instances[0]!

    setHidden(true)
    await vi.advanceTimersByTimeAsync(4_000)
    expect(first.closed).toBe(false)
    await vi.advanceTimersByTimeAsync(1_000)
    expect(first.closed).toBe(true)

    setHidden(false)
    await vi.advanceTimersByTimeAsync(0)
    expect(FakeEventSource.instances).toHaveLength(2)
    expect(FakeEventSource.instances[1]!.url).toContain('token=maps-stream-token')
    store.disconnect()
  })

  it('keeps the stream across a quick tab switch', async () => {
    const store = newService()
    await store.connectToMap('b')

    setHidden(true)
    await vi.advanceTimersByTimeAsync(2_000)
    setHidden(false)
    await vi.advanceTimersByTimeAsync(60_000)

    expect(FakeEventSource.instances).toHaveLength(1)
    expect(FakeEventSource.instances[0]!.closed).toBe(false)
    store.disconnect()
  })

  it('opens no stream for a map opened in a background tab until it is looked at', async () => {
    hidden = true
    const store = newService()
    await store.connectToMap('b')
    expect(FakeEventSource.instances).toHaveLength(0)

    setHidden(false)
    await vi.advanceTimersByTimeAsync(0)
    expect(FakeEventSource.instances).toHaveLength(1)
    store.disconnect()
  })

  it('does not reopen a paused stream when the credential rotates', async () => {
    const store = newService()
    await store.connectToMap('b')
    setHidden(true)
    await vi.advanceTimersByTimeAsync(5_000)

    store.reconnectStream()
    await vi.advanceTimersByTimeAsync(0)

    expect(FakeEventSource.instances).toHaveLength(1)
    store.disconnect()
  })
})
