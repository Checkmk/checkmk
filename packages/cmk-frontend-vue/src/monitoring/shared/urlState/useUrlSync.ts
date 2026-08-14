/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { watch } from 'vue'

import { type UrlSync, browserUrlSync } from '@/monitoring/shared/browserUrlSync'
import { mergeQuery } from '@/monitoring/shared/urlQuery'

import type { UrlStateWriter } from './types'

/**
 * The single owner of a page's address bar: it merges every registered slice
 * into one write, so key ownership is settled at registration instead of by
 * whichever writer ran last.
 */
class UrlStateSync {
  private readonly claimedBy: Map<string, string> = new Map()
  /** Keys actually put in the URL by the last flush, so dropping one clears it. */
  private lastWritten: Set<string> = new Set()

  constructor(
    private readonly writers: readonly UrlStateWriter[],
    private readonly urlSync: UrlSync
  ) {
    for (const writer of writers) {
      for (const key of writer.keys) {
        const owner = this.claimedBy.get(key)
        if (owner !== undefined) {
          throw new Error(
            `useUrlSync: '${writer.name}' claims the URL param '${key}', which '${owner}' already owns`
          )
        }
        this.claimedBy.set(key, writer.name)
      }
    }
  }

  /**
   * Collects every slice's current params and writes them in one go. Keys the
   * previous flush wrote and this one does not are set to `null`, which is what
   * lets a slice with a runtime vocabulary clean up after itself.
   */
  flush(): void {
    const updates: Record<string, string | null> = {}
    for (const key of this.lastWritten) {
      updates[key] = null
    }

    const written = new Set<string>()
    for (const writer of this.writers) {
      for (const [key, value] of Object.entries(writer.params.value)) {
        const owner = this.claimedBy.get(key)
        if (owner !== undefined && owner !== writer.name) {
          console.error(
            `useUrlSync: '${writer.name}' tried to write the URL param '${key}', which '${owner}' owns; ignored it`
          )
          continue
        }
        updates[key] = value
        if (value !== null) {
          written.add(key)
        }
      }
    }
    this.lastWritten = written

    const { pathname, search, hash } = this.urlSync.getCurrentUrl()
    const merged = mergeQuery(search, updates)
    if (merged === search) {
      return
    }
    this.urlSync.replaceUrl(`${pathname}${merged}${hash}`)
  }
}

export interface UseUrlSyncOptions {
  /**
   * Where to read the current address bar and write updates to. Defaults to
   * the real browser URL via {@link browserUrlSync}.
   */
  urlSync?: UrlSync
}

/**
 * Mirrors every given slice of URL-owned state into the address bar, and owns
 * `window.history` for the page while doing it.
 *
 * One owner rather than one writer per slice, because the slices share an
 * address bar they each only partly understand: `mergeQuery` keeps the params
 * nobody claimed, the registration check rejects two slices claiming the same
 * param, and collecting all of them into a single write means a plain page load
 * produces one `replaceState` at most - and none at all when the URL already
 * says what the state does.
 *
 * A duplicate claim throws rather than degrading: it depends on nothing but
 * which slices a page registers, so it can only ever fire in every run,
 * including the tests, and never for a subset of users or URLs.
 *
 * Deliberately not part of {@link MonitoringService}: `FlowService` extends the
 * same base but spells its filters out as legacy filter vars, so it is a third
 * slice here rather than a second mechanism.
 */
export function useUrlSync(
  writers: readonly UrlStateWriter[],
  options: UseUrlSyncOptions = {}
): void {
  const { urlSync = browserUrlSync } = options
  const sync = new UrlStateSync(writers, urlSync)
  watch(
    writers.map((writer) => writer.params),
    () => sync.flush(),
    { immediate: true }
  )
}
