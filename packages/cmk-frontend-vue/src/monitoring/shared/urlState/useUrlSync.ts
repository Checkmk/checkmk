/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onScopeDispose, watch } from 'vue'

import { type UrlSync, browserUrlSync } from '@/monitoring/shared/browserUrlSync'
import { mergeQuery, parseQuery } from '@/monitoring/shared/urlQuery'

import type { UrlStateTarget, UrlStateWriter } from './types'

const TARGETS: readonly UrlStateTarget[] = ['query', 'hash']

function targetOf(writer: UrlStateWriter): UrlStateTarget {
  return writer.target ?? 'query'
}

/** Both halves are handled as bare param bodies; only the final URL carries `?` and `#`. */
function body(value: string): string {
  return value.startsWith('?') || value.startsWith('#') ? value.slice(1) : value
}

function mergeParams(source: string, updates: Record<string, string | null>): string {
  return body(mergeQuery(source, updates))
}

function decodeValue(raw: string): string {
  try {
    return decodeURIComponent(raw.replace(/\+/g, ' '))
  } catch {
    return raw
  }
}

/** The params a target currently spells, for handing to a slice's `apply`. */
function currentParams(source: string): Record<string, string> {
  const params: Record<string, string> = {}
  for (const segment of parseQuery(source)) {
    const separator = segment.raw.indexOf('=')
    params[segment.key] = separator === -1 ? '' : decodeValue(segment.raw.slice(separator + 1))
  }
  return params
}

/**
 * The single owner of a page's address bar: it merges every registered slice
 * into one write, so key ownership is settled at registration instead of by
 * whichever writer ran last.
 */
class UrlStateSync {
  private readonly claimedBy: Map<string, string> = new Map()
  /** Keys actually put in the URL by the last flush, per target. */
  private readonly lastWritten: Map<UrlStateTarget, Set<string>> = new Map()

  constructor(
    private readonly writers: readonly UrlStateWriter[],
    private readonly urlSync: UrlSync
  ) {
    for (const writer of writers) {
      for (const key of writer.keys) {
        const claim = `${targetOf(writer)}:${key}`
        const owner = this.claimedBy.get(claim)
        if (owner !== undefined) {
          throw new Error(
            `useUrlSync: '${writer.name}' claims the URL param '${key}', which '${owner}' already owns`
          )
        }
        this.claimedBy.set(claim, writer.name)
      }
    }
  }

  /**
   * Collects every slice's current params and writes them in one go. Keys the
   * previous flush wrote and this one does not are set to `null`, which is what
   * lets a slice with a runtime vocabulary clean up after itself.
   */
  flush(): void {
    const { pathname, search, hash } = this.urlSync.getCurrentUrl()
    const sources: Record<UrlStateTarget, string> = { query: body(search), hash: body(hash) }
    const merged: Record<UrlStateTarget, string> = { ...sources }
    let push = false

    for (const target of TARGETS) {
      const updates: Record<string, string | null> = {}
      for (const key of this.lastWritten.get(target) ?? []) {
        updates[key] = null
      }

      const written = new Set<string>()
      for (const writer of this.writers.filter((candidate) => targetOf(candidate) === target)) {
        for (const [key, value] of Object.entries(writer.params.value)) {
          const owner = this.claimedBy.get(`${target}:${key}`)
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
      this.lastWritten.set(target, written)
      merged[target] = mergeParams(sources[target], updates)
      const wantsHistory = this.writers.some(
        (writer) => targetOf(writer) === target && writer.history === 'push'
      )
      if (wantsHistory && merged[target] !== sources[target]) {
        push = true
      }
    }

    if (merged.query === sources.query && merged.hash === sources.hash) {
      return
    }
    const query = merged.query === '' ? '' : `?${merged.query}`
    const fragment = merged.hash === '' ? '' : `#${merged.hash}`
    const url = `${pathname}${query}${fragment}`
    if (push) {
      this.urlSync.pushUrl(url)
      return
    }
    this.urlSync.replaceUrl(url)
  }

  /** Hands each slice what the URL says now, after the user walked the history. */
  applyCurrentUrl(): void {
    const { search, hash } = this.urlSync.getCurrentUrl()
    const params: Record<UrlStateTarget, Record<string, string>> = {
      query: currentParams(search),
      hash: currentParams(body(hash))
    }
    for (const writer of this.writers) {
      writer.apply?.(params[targetOf(writer)])
    }
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
 * produces one write at most - and none at all when the URL already says what
 * the state does.
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
  if (writers.some((writer) => writer.apply !== undefined)) {
    onScopeDispose(urlSync.onNavigate(() => sync.applyCurrentUrl()))
  }
}
