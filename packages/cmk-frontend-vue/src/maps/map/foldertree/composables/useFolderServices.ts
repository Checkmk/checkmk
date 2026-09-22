/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * A folder tree's service leaves, which are not in the tree the daemon sends.
 *
 * Pushing every host's services over the state stream would not survive a site
 * with millions of them, so they arrive two ways instead. A host the operator
 * drills into has its services fetched once and kept live afterwards. And a
 * `s:` search is answered by the server, because a service nobody has drilled
 * into is not in the browser to be searched -- which is also how a search knows
 * which hosts to reveal at all.
 *
 * Both feed one lookup, in which a drilled-into host's full list wins over the
 * search's partial one.
 */
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type ComputedRef, computed, reactive, ref, watch } from 'vue'

import { useMapsApis, useStates } from '@/maps/services/context'
import type { FolderHostService, FolderTreeNode } from '@/maps/types/api'

import type { FilterTerm } from '../filter'

/** How long to wait for the typing to stop before asking the server. */
const SEARCH_DEBOUNCE_MS = 250
/** Shorter needles are too broad to be worth a Livestatus query; the backend
 *  applies the same floor. */
const MIN_NEEDLE = 2
/** How often the fetched leaves are refreshed while the map is open. */
const REFRESH_INTERVAL_MS = 4000

interface FolderServicesOptions {
  mapName: () => string | null
  preview: () => boolean
  /** Whether the map offers drilling into a host at all. */
  showServices: () => boolean
  terms: () => FilterTerm[]
}

export interface FolderServices {
  /** A host's service leaves, by host name. */
  byHost: ComputedRef<Record<string, FolderTreeNode[]>>
  loading: ReadonlySet<string>
  failed: ReadonlySet<string>
  /** Hosts the server's search matched, which is what a `s:` query filters on. */
  matchedHosts: ComputedRef<Set<string>>
  /** Whether the server had more matches than it was willing to return. */
  truncated: ComputedRef<boolean>
  /**
   * Whether the server search has yet to answer the query on screen -- a
   * request is in flight, or the needle is still too short to send. The tree
   * holds its previous matches until it settles, rather than flashing empty.
   */
  unsettled: ComputedRef<boolean>
  /** Fetch a host's services, unless they are already there or on their way. */
  ensure: (host: FolderTreeNode) => Promise<void>
}

/** A fetched service as a leaf of the tree, so both drawings can walk it like
 *  any other node. */
function toServiceNode(
  service: FolderHostService,
  pathPrefix: string,
  siteId: string | null
): FolderTreeNode {
  return {
    path: `${pathPrefix}/${service.name}`,
    title: service.name,
    kind: 'service',
    state: service.state,
    is_empty: false,
    folder_id: '',
    host_count: 0,
    problem_count: 0,
    severity_counts: {},
    output: service.output,
    acknowledged: service.acknowledged,
    in_downtime: service.in_downtime,
    is_flapping: service.is_flapping,
    stale: false,
    last_state_change: service.last_state_change ?? null,
    site_id: siteId,
    children: []
  }
}

export function useFolderServices(options: FolderServicesOptions): FolderServices {
  const { mapStates } = useMapsApis()
  const states = useStates()

  // Services of the hosts the operator drilled into, and where they came from
  // so they can be refetched in place on every live refresh.
  const fetched = reactive<Record<string, FolderTreeNode[]>>({})
  const loading = reactive(new Set<string>())
  const failed = reactive(new Set<string>())
  const origins = reactive<Record<string, { path: string; siteId: string | null }>>({})

  // The server search's own snapshot, keyed by host.
  const matches = reactive<Record<string, FolderTreeNode[]>>({})
  const truncated = ref(false)
  const pending = ref(false)

  const needles = computed(() => {
    const longEnough = (needle: string) => needle.length >= MIN_NEEDLE
    const of = (field: string) =>
      options
        .terms()
        .filter((term) => term.field === field)
        .map((term) => term.needle)
        .filter(longEnough)
    return { s: of('service'), h: of('host'), q: of('any') }
  })
  const searchable = computed(() => needles.value.s.length > 0 || needles.value.q.length > 0)
  // A query the server answers. Used to hold the "no matches" state back while
  // the needle is still too short or a request is in flight.
  const serverAnswerable = computed(() =>
    options.terms().some((term) => term.field === 'service' || term.field === 'any')
  )

  // Which map everything cached here belongs to. A fetch started on one map can
  // only land after the view has moved to the next, where the same host name may
  // well exist again -- and nothing would correct it afterwards, because the
  // switch dropped the host from `origins` and with it from the refresh loop. So
  // an answer from a map that is no longer on screen is thrown away, the way the
  // search discards a superseded query.
  let generation = 0

  async function fetchServices(host: string, path: string, siteId: string | null): Promise<void> {
    const name = options.mapName()
    if (!name) {
      return
    }
    const sequence = generation
    const services = await mapStates.fetchFolderHostServices(name, host)
    if (sequence !== generation) {
      return
    }
    fetched[host] = services.map((service) => toServiceNode(service, path, siteId))
    // The refresh reaches this too, so a host that recovered stops being an
    // error row while its services are already back.
    failed.delete(host)
  }

  async function ensure(host: FolderTreeNode): Promise<void> {
    const name = host.title
    if (!options.showServices() || !options.mapName()) {
      return
    }
    if (fetched[name] || loading.has(name)) {
      return
    }
    const sequence = generation
    origins[name] = { path: host.path, siteId: host.site_id ?? null }
    loading.add(name)
    failed.delete(name)
    try {
      await fetchServices(name, host.path, host.site_id ?? null)
    } catch {
      if (sequence === generation) {
        failed.add(name)
      }
    } finally {
      if (sequence === generation) {
        loading.delete(name)
      }
    }
  }

  function clearMatches(): void {
    for (const host of Object.keys(matches)) {
      delete matches[host]
    }
    truncated.value = false
  }

  // Typing and the periodic refresh fire independent requests, so a slow older
  // response could otherwise overwrite a newer query's matches -- and the
  // matched hosts would then disagree with what is in the search box. Only the
  // newest request is allowed to write. Clearing the box counts as a newer
  // request: it takes a sequence number before returning, so the one still in
  // flight cannot write the emptied query's matches back.
  let latest = 0

  async function search(): Promise<void> {
    const name = options.mapName()
    const sequence = ++latest
    if (options.preview() || !name || !searchable.value) {
      clearMatches()
      pending.value = false
      return
    }
    pending.value = true
    try {
      const result = await mapStates.searchFolderServices(name, needles.value)
      if (sequence !== latest) {
        return
      }
      const seen = new Set<string>()
      for (const match of result.matches) {
        seen.add(match.host)
        matches[match.host] = match.services.map((service) =>
          toServiceNode(service, match.host, match.site_id ?? null)
        )
      }
      for (const host of Object.keys(matches)) {
        if (!seen.has(host)) {
          delete matches[host]
        }
      }
      truncated.value = result.truncated
    } catch {
      if (sequence === latest) {
        clearMatches()
      }
    } finally {
      if (sequence === latest) {
        pending.value = false
      }
    }
  }

  const searchSoon = useDebounceFn(search, SEARCH_DEBOUNCE_MS)
  // Marked pending the moment the query changes, before the debounce fires, so
  // the empty state stays suppressed through the wait and not just the request.
  watch(needles, () => {
    if (searchable.value) {
      pending.value = true
    }
    void searchSoon()
  })

  // The view is reused when the map changes, so everything cached here has to
  // go with the map it was fetched for: a host of the same name on the next map
  // would otherwise draw with the previous map's services. The in-flight
  // requests are invalidated with it, answers included.
  watch(
    () => options.mapName(),
    () => {
      ++latest
      ++generation
      for (const host of Object.keys(fetched)) {
        delete fetched[host]
      }
      for (const host of Object.keys(origins)) {
        delete origins[host]
      }
      loading.clear()
      failed.clear()
      clearMatches()
      pending.value = false
    }
  )

  // Keep what has been loaded live: the leaves sit outside the state stream, so
  // a downtime set after a host was opened would otherwise never show up. The
  // work is bounded by what the operator actually drilled into; an active search
  // rides on the same tick as one further query, whatever it matched.
  let lastRefresh = 0
  watch(
    () => states.folderTreeVersion.value,
    () => {
      const now = Date.now()
      if (now - lastRefresh < REFRESH_INTERVAL_MS) {
        return
      }
      lastRefresh = now
      for (const [host, origin] of Object.entries(origins)) {
        void fetchServices(host, origin.path, origin.siteId).catch(() => {})
      }
      if (searchable.value) {
        void search()
      }
    }
  )

  return {
    byHost: computed(() => ({ ...matches, ...fetched })),
    loading,
    failed,
    matchedHosts: computed(() => new Set(Object.keys(matches))),
    truncated: computed(() => truncated.value),
    unsettled: computed(() => serverAnswerable.value && (pending.value || !searchable.value)),
    ensure
  }
}
