/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { computed, ref } from 'vue'

import type { ConnectionsApi } from '@/maps/api/connections'
import type { SignedMap } from '@/maps/api/mapConfig'
import type { MapStatesApi } from '@/maps/api/mapStates'
import type { MonitoringObjectsApi } from '@/maps/api/monitoringObjects'
import type { MapService } from '@/maps/services/MapService'
import { MapStatesService } from '@/maps/services/MapStatesService'
import type { MapsAuthService } from '@/maps/services/MapsAuthService'
import type { MapConfig, MapStates } from '@/maps/types/api'

import { aMap, aMapAccess, aState, aTopologyNode, anObject } from '../support/fixtures'

// What the connection itself does — opening, falling back to polling, healing —
// belongs to the shared stream client and is covered there. What is maps' own is
// what the events mean: how a tick is merged, how a folder-tree delta is applied,
// and which entries the daemon does not own.

/** Minimal EventSource stand-in that lets a test drive the stream. */
class FakeEventSource {
  static instances: FakeEventSource[] = []
  static readonly OPEN = 1
  static readonly CLOSED = 2
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  readyState = 0
  closed = false
  private readonly listeners = new Map<string, (e: MessageEvent<string>) => void>()
  constructor(public url: string) {
    FakeEventSource.instances.push(this)
  }
  addEventListener(name: string, listener: (e: MessageEvent<string>) => void) {
    this.listeners.set(name, listener)
  }
  close() {
    this.closed = true
    this.readyState = 2
  }
  emit(name: string, data: unknown) {
    this.listeners.get(name)?.(new MessageEvent(name, { data: JSON.stringify(data) }))
  }
  failToOpen() {
    this.readyState = FakeEventSource.CLOSED
    this.onerror?.()
  }
}

const emptyStates: MapStates = {
  map_name: 'b',
  states: [],
  generated_at: 1,
  connection_ok: true,
  dead_sites: [],
  folder_tree: null,
  runtime: { state_refresh_interval: 5 }
}

// Every service is torn down after its test: an undisconnected one keeps its
// visibility listener and would answer another test's tab switch.
const services: MapStatesService[] = []
afterEach(() => {
  for (const service of services.splice(0)) {
    service.disconnect()
  }
})

const freshlySigned: SignedMap = {
  config: aMap({ name: 'b' }),
  config_b64: 'fresh',
  sig: 'fresh-sig',
  access: aMapAccess({ owner: '' }),
  map_link_titles: {}
}

type StatesApi = Pick<
  MapStatesApi,
  'register' | 'registerEdit' | 'registerSavedOnly' | 'fetchStates'
>

function newService(
  map: MapConfig | null = null,
  objectOverrides: Partial<
    Pick<MonitoringObjectsApi, 'fetchAggregationStates' | 'fetchAggregationTree'>
  > = {},
  statesOverrides: Partial<StatesApi> = {},
  session: {
    refresh?: Pick<MapsAuthService, 'refresh'>['refresh']
    getSignedMap?: Pick<MapService, 'getSignedMap'>['getSignedMap']
    mapOwner?: string
  } = {}
): MapStatesService {
  const statesApi: StatesApi = {
    register: vi.fn().mockResolvedValue(emptyStates),
    registerEdit: vi.fn().mockResolvedValue(emptyStates),
    registerSavedOnly: vi.fn().mockResolvedValue(undefined),
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
    refresh: session.refresh ?? vi.fn().mockResolvedValue(true),
    user: computed(() => ({
      user_id: 'me',
      is_admin: true,
      language: 'en',
      can_configure: true,
      can_create_maps: true,
      command_permissions: []
    }))
  }
  const service = new MapStatesService(statesApi, connections, objects, auth, {
    currentMap: ref(map),
    currentMapAccess: ref(aMapAccess({ owner: session.mapOwner ?? 'me' })),
    getSignedMap: session.getSignedMap ?? vi.fn().mockResolvedValue(freshlySigned)
  })
  services.push(service)
  return service
}

describe('MapStatesService — folder-tree delta apply', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
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
    es.emit('state_update', {
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

describe('MapStatesService — topology update', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('takes the nodes of a full topology update as the topology', async () => {
    const store = newService()
    await store.connectToMap('b')

    FakeEventSource.instances[0]!.emit('topology_update', {
      type: 'topology_update',
      map: 'b',
      delta: {
        full: true,
        generated_at: 7,
        added: [aTopologyNode({ name: 'h1' })],
        changed: [],
        removed: [],
        timing: []
      }
    })

    expect(store.topology.value.map((n) => n.name)).toEqual(['h1'])
    expect(store.topologyReady.value).toBe(true)
  })
})

describe('MapStatesService — stream URL', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  // The browser sends the session cookie with the stream request, so a URL that
  // can reach an access log carries no credential.
  it('opens the stream of the map without a credential in the URL', async () => {
    const store = newService()
    await store.connectToMap('b')
    const url = new URL(FakeEventSource.instances[0]!.url)
    expect(url.pathname).toMatch(/\/maps\/api\/v1\/sse\/maps\/b$/)
    expect(url.search).toBe('')
  })
})

describe('MapStatesService — BI aggregations resolve GUI-side', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  it('merges the resolved state and tree, and keeps them across a full resend', async () => {
    const map = aMap({
      objects: [
        anObject({ id: 'agg1', type: 'aggregation', aggregation_id: 'Host x', expand_depth: 2 })
      ]
    })
    const objects = {
      fetchAggregationStates: vi.fn().mockResolvedValue({
        'Host x': { state: 'CRITICAL', output: 'crit', acknowledged: false, in_downtime: false }
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
    FakeEventSource.instances[0]!.emit('state_update', {
      type: 'state_update',
      map: 'map1',
      full: true,
      removed_ids: [],
      timing: [],
      states: { ...emptyStates, map_name: 'map1' }
    })

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

  it('knows no state of a map the core never answered for', async () => {
    const coreDown = { ...emptyStates, connection_ok: false }
    const store = newService(null, {}, { fetchStates: vi.fn().mockResolvedValue(coreDown) })

    await store.connectToMap('b')

    expect(store.lastUpdate.value).not.toBeNull()
    expect(store.liveStatus.value).toBe('unreachable')
  })

  it('keeps what it knew once the core stops answering', async () => {
    const fetchStates = vi
      .fn()
      .mockResolvedValueOnce(emptyStates)
      .mockResolvedValue({ ...emptyStates, connection_ok: false })
    const store = newService(null, {}, { fetchStates })
    await store.connectToMap('b')
    expect(store.liveStatus.value).toBe('live')

    await store.refresh()

    expect(store.liveStatus.value).toBe('lost')
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
    expect(FakeEventSource.instances[1]!.url).toMatch(/\/api\/v1\/sse\/maps\/b$/)
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
})

describe('MapStatesService — refused a stream', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('asks for the states at the interval the daemon fetches them', async () => {
    const atSeven = {
      ...emptyStates,
      runtime: { ...emptyStates.runtime, state_refresh_interval: 7 }
    }
    const fetchStates = vi.fn().mockResolvedValue(atSeven)
    const store = newService(null, {}, { fetchStates })
    await store.connectToMap('b')
    FakeEventSource.instances[0]!.failToOpen()
    await vi.advanceTimersByTimeAsync(0)
    const asked = fetchStates.mock.calls.length

    await vi.advanceTimersByTimeAsync(6_999)
    expect(fetchStates).toHaveBeenCalledTimes(asked)
    await vi.advanceTimersByTimeAsync(1)
    expect(fetchStates).toHaveBeenCalledTimes(asked + 1)
  })
})

describe('MapStatesService — overlapping connects', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  // A caller that goes on to ask the daemon about the map must not run ahead of
  // the registration the first connect is still doing.
  it('lets an overlapping connect wait until the map is registered', async () => {
    let registered = false
    const register = vi.fn(async () => {
      await Promise.resolve()
      registered = true
      return emptyStates
    })
    const store = newService(null, {}, { register })
    const signed = { config_b64: 'x', sig: 'y' }

    const first = store.connectToMap('b', signed)
    await store.connectToMap('b', signed)

    expect(registered).toBe(true)
    expect(register).toHaveBeenCalledTimes(1)
    await first
  })

  it('opens no stream for a connect a later one took over from', async () => {
    let answerFirst: (states: MapStates) => void = () => undefined
    const register = vi
      .fn()
      .mockReturnValueOnce(new Promise<MapStates>((resolve) => (answerFirst = resolve)))
      .mockResolvedValue(emptyStates)
    const store = newService(null, {}, { register })
    const signed = { config_b64: 'x', sig: 'y' }

    const first = store.connectToMap('back_map', signed)
    await vi.waitFor(() => expect(register).toHaveBeenCalledOnce())
    await store.connectToMap('other_map', signed)
    await store.connectToMap('back_map', signed)
    answerFirst(emptyStates)
    await first

    expect(FakeEventSource.instances.map((source) => source.url)).toEqual([
      expect.stringContaining('other_map'),
      expect.stringContaining('back_map')
    ])
  })

  it('opens a stream for a map returned to while its last connect still ran', async () => {
    const register = vi
      .fn()
      .mockReturnValueOnce(new Promise<MapStates>(() => {}))
      .mockResolvedValue(emptyStates)
    const store = newService(null, {}, { register })
    const signed = { config_b64: 'x', sig: 'y' }

    void store.connectToMap('back_map', signed)
    await vi.waitFor(() => expect(register).toHaveBeenCalledOnce())
    store.disconnect()
    await store.connectToMap('back_map', signed)

    expect(FakeEventSource.instances.map((source) => source.url)).toEqual([
      expect.stringContaining('back_map')
    ])
  })

  it('shows no error of a map that was left on the one opened', async () => {
    let failFirst: (error: Error) => void = () => undefined
    const register = vi
      .fn()
      .mockReturnValueOnce(new Promise<MapStates>((_resolve, reject) => (failFirst = reject)))
      .mockResolvedValue(emptyStates)
    const store = newService(null, {}, { register })
    const signed = { config_b64: 'x', sig: 'y' }

    const first = store.connectToMap('left_map', signed)
    await vi.waitFor(() => expect(register).toHaveBeenCalledOnce())
    await store.connectToMap('opened_map', signed)
    failFirst(new Error('Forbidden'))
    await expect(first).rejects.toThrow('Forbidden')

    expect(store.loadError.value).toBeNull()
  })
})

describe('MapStatesService — opening a map', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  it('shows the states registering answered with, without asking again', async () => {
    const register = vi.fn().mockResolvedValue({
      ...emptyStates,
      states: [aState({ object_id: 'h1', type: 'host', state: 'DOWN' })]
    })
    const fetchStates = vi.fn().mockResolvedValue(emptyStates)
    const store = newService(null, {}, { register, fetchStates })

    await store.connectToMap('b', { config_b64: 'x', sig: 'y' })

    expect(store.getState('h1')?.state).toBe('DOWN')
    expect(fetchStates).not.toHaveBeenCalled()
  })

  it('asks for the states itself when registering could not answer with them', async () => {
    const register = vi.fn().mockRejectedValue(new CmkApiError('HTTP 429', null, '', 429))
    const fetchStates = vi.fn().mockResolvedValue({
      ...emptyStates,
      states: [aState({ object_id: 'h1', type: 'host', state: 'UP' })]
    })
    const store = newService(null, {}, { register, fetchStates })

    await store.connectToMap('b', { config_b64: 'x', sig: 'y' })

    expect(store.getState('h1')?.state).toBe('UP')
  })

  it('keeps the states of the newest edit when an older one answers last', async () => {
    let answerOlder: (states: MapStates) => void = () => undefined
    const registerEdit = vi
      .fn()
      .mockReturnValueOnce(new Promise<MapStates>((resolve) => (answerOlder = resolve)))
      .mockResolvedValueOnce({
        ...emptyStates,
        states: [aState({ object_id: 'h2', type: 'host', state: 'UP' })]
      })
    const store = newService(aMap({ name: 'b' }), {}, { registerEdit })
    await store.connectToMap('b', { config_b64: 'x', sig: 'y' })

    const older = store.reregister(aMap({ name: 'b' }))
    await store.reregister(aMap({ name: 'b' }))
    answerOlder(emptyStates)
    await older

    expect(store.getState('h2')?.state).toBe('UP')
  })

  it("does not hand the daemon an unsaved edit of another user's map", async () => {
    const registerEdit = vi.fn().mockResolvedValue(emptyStates)
    const store = newService(aMap({ name: 'b' }), {}, { registerEdit }, { mapOwner: 'someone' })
    await store.connectToMap('b', { config_b64: 'x', sig: 'y' })

    await store.reregister(aMap({ name: 'b' }))

    expect(registerEdit).not.toHaveBeenCalled()
  })

  it('asks registering for the states of a settings preview', async () => {
    const registerEdit = vi.fn().mockResolvedValue(emptyStates)
    const store = newService(aMap({ name: 'b' }), {}, { registerEdit })
    await store.connectToMap('b', { config_b64: 'x', sig: 'y' })
    store.radarOverride.value = { filter: 'hostgroup', filterValue: 'web' }

    await store.reregister(aMap({ name: 'b' }))

    expect(registerEdit).toHaveBeenCalledWith(expect.anything(), {
      radar: { filter: 'hostgroup', filterValue: 'web' },
      folder: null
    })
  })
})

describe('MapStatesService — a daemon that lost the map', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  const failure = (status: number) => new CmkApiError(`HTTP ${status}`, null, '', status)
  const signed = { config_b64: 'x', sig: 'y' }

  // The daemon keeps registrations in memory, so a restart forgets every map.
  it('registers the map again, signed afresh, and carries on', async () => {
    const register = vi.fn().mockResolvedValue(emptyStates)
    const fetchStates = vi.fn().mockResolvedValue(emptyStates)
    const getSignedMap = vi.fn().mockResolvedValue(freshlySigned)
    const store = newService(null, {}, { register, fetchStates }, { getSignedMap })
    await store.connectToMap('b', signed)
    fetchStates.mockRejectedValueOnce(failure(404))

    await store.refresh()

    expect(getSignedMap).toHaveBeenCalledWith('b')
    expect(register).toHaveBeenLastCalledWith('b', freshlySigned, { radar: null, folder: null }, {})
    expect(store.connected.value).toBe(true)
  })

  it('checks the session instead of registering again when the daemon refuses it', async () => {
    const register = vi.fn().mockResolvedValue(emptyStates)
    const fetchStates = vi.fn().mockResolvedValue(emptyStates)
    const refresh = vi.fn().mockResolvedValue(false)
    const store = newService(null, {}, { register, fetchStates }, { refresh })
    await store.connectToMap('b', signed)
    fetchStates.mockRejectedValueOnce(failure(401))

    await store.refresh()

    expect(refresh).toHaveBeenCalledTimes(1)
    expect(register).toHaveBeenCalledTimes(1)
    expect(store.connected.value).toBe(false)
  })

  it('does not register again for a failure that is not about the map', async () => {
    const register = vi.fn().mockResolvedValue(emptyStates)
    const fetchStates = vi.fn().mockResolvedValue(emptyStates)
    const store = newService(null, {}, { register, fetchStates })
    await store.connectToMap('b', signed)
    fetchStates.mockRejectedValueOnce(failure(500))

    await store.refresh()

    expect(register).toHaveBeenCalledTimes(1)
    expect(store.connected.value).toBe(false)
  })

  it('opens the stream again once the restarted daemon took the map back', async () => {
    const fetchStates = vi.fn().mockResolvedValue(emptyStates)
    const store = newService(null, {}, { fetchStates })
    await store.connectToMap('b', signed)
    fetchStates.mockRejectedValueOnce(failure(404))

    FakeEventSource.instances[0]!.failToOpen()

    await vi.waitFor(() => expect(FakeEventSource.instances).toHaveLength(2))
    expect(store.streamAvailable.value).toBe(true)
  })
})

describe('MapStatesService — saved settings', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  // The daemon takes a preview only of the caller's own map.
  it('registers the saved map signed, not as a preview, telling the open views', async () => {
    const register = vi.fn().mockResolvedValue(emptyStates)
    const getSignedMap = vi.fn().mockResolvedValue(freshlySigned)
    const store = newService(null, {}, { register }, { getSignedMap })
    await store.connectToMap('b', { config_b64: 'x', sig: 'y' })

    await store.reregisterSavedWithIndicator()

    expect(getSignedMap).toHaveBeenCalledWith('b')
    expect(register).toHaveBeenLastCalledWith(
      'b',
      freshlySigned,
      { radar: null, folder: null },
      { saved: true }
    )
  })
})

describe('MapStatesService — a saved map', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  const saved = { config_b64: 's', sig: 'v2' }

  it("hands the daemon another user's open map as it was saved, with its states", async () => {
    const register = vi.fn().mockResolvedValue(emptyStates)
    const store = newService(null, {}, { register }, { mapOwner: 'someone' })
    await store.connectToMap('b', { config_b64: 'x', sig: 'v1' })

    await store.registerSaved('b', saved)

    expect(register).toHaveBeenLastCalledWith(
      'b',
      saved,
      { radar: null, folder: null },
      { saved: true }
    )
  })

  it("hands the daemon the user's own open map as it was saved, without asking for its states", async () => {
    const register = vi.fn().mockResolvedValue(emptyStates)
    const registerSavedOnly = vi.fn().mockResolvedValue(undefined)
    const store = newService(null, {}, { register, registerSavedOnly })
    await store.connectToMap('b', { config_b64: 'x', sig: 'v1' })
    register.mockClear()

    await store.registerSaved('b', saved)

    expect(registerSavedOnly).toHaveBeenCalledWith('b', saved)
    expect(register).not.toHaveBeenCalled()
  })

  it('hands the daemon the stored map shown again after a refused save, with its states', async () => {
    const register = vi.fn().mockResolvedValue(emptyStates)
    const store = newService(null, {}, { register })
    await store.connectToMap('b', { config_b64: 'x', sig: 'v1' })

    await store.registerSaved('b', saved, { restored: true })

    expect(register).toHaveBeenLastCalledWith('b', saved, { radar: null, folder: null })
  })

  it('carries on when the daemon is busy with a save of the own map', async () => {
    const registerSavedOnly = vi.fn().mockRejectedValue(new CmkApiError('HTTP 503', null, '', 503))
    const store = newService(null, {}, { registerSavedOnly })
    await store.connectToMap('b', { config_b64: 'x', sig: 'v1' })

    await expect(store.registerSaved('b', saved)).resolves.toBeUndefined()
  })

  it('hands the daemon a map saved on the way out of it, without asking for its states', async () => {
    const registerSavedOnly = vi.fn().mockResolvedValue(undefined)
    const store = newService(null, {}, { registerSavedOnly }, { mapOwner: 'someone' })
    await store.connectToMap('other', { config_b64: 'x', sig: 'v1' })

    await store.registerSaved('b', saved)

    expect(registerSavedOnly).toHaveBeenCalledWith('b', saved)
  })

  it('tells which version the stream says was saved', async () => {
    const listener = vi.fn()
    const store = newService()
    store.onMapSaved(listener)
    await store.connectToMap('b', { config_b64: 'x', sig: 'v1' })

    FakeEventSource.instances[0]!.emit('map_saved', { type: 'map_saved', map: 'b', sig: 'v2' })

    expect(listener).toHaveBeenCalledWith('b', 'v2')
  })
})
