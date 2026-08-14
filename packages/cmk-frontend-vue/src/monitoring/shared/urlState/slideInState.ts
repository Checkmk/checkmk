/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, ref, watch } from 'vue'

import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

import type { UrlStateWriter } from './types'

const TAB_KEY = 'tab'

/**
 * What a page needs to say to name its open detail panel in the URL, and to get
 * that row back.
 *
 * Every listing opens its panel from a whole row - the panel header reads state,
 * links and labels off it - but a URL can only carry an identity, so which
 * fields identify a row is the page's decision: an all hosts row is a site plus
 * a name, a host services row is a description, because there the host is the
 * page. {@link load} is the other half of that decision: a shared link has to
 * open the panel even when the listing does not show that row, so the page says
 * how to fetch one by identity.
 */
export interface SlideInUrlDescriptor<TRow, TIdentity> {
  /** Params identifying the row on show, `tab` excluded - that one is shared. */
  readonly keys: readonly string[]
  /** The tab an opening starts on; omitted from the URL as it says nothing. */
  readonly defaultTabId?: string
  encode(row: TRow): Record<string, string>
  /** The identity the URL names, or `null` when it names none. */
  decode(params: Record<string, string>): TIdentity | null
  matches(row: TRow, identity: TIdentity): boolean
  /**
   * Fetches the row an identity names, for a link into a listing that does not
   * show it - filtered out, on a later page, or in a state it has since left.
   * `null` when it does not exist, or the user may not see it: this goes
   * through the same authorised endpoint the listing does, so a fragment can
   * never open a row a request would not have returned.
   */
  load(identity: TIdentity): Promise<TRow | null>
}

const REGEX_METACHARACTERS = /[.*+?^${}()|[\]\\]/g

/**
 * An anchored pattern matching `value` and nothing else, for a `matches`
 * condition standing in for the equality operator the string fields do not
 * offer. Every metacharacter is escaped, so a host called `web.01` cannot match
 * `webX01` and a name out of a URL cannot smuggle a pattern of its own.
 */
export function exactPattern(value: string): string {
  return `^${value.replace(REGEX_METACHARACTERS, '\\$&')}$`
}

/** The panel state a URL fragment names, or `null` when it names no panel at all. */
export interface SlideInUrlState<TIdentity> {
  identity: TIdentity
  tabId: string | undefined
  /** The fragment's own params, kept verbatim so an unopened link is left alone. */
  params: Record<string, string>
}

function parseFragment(hash: string): Record<string, string> {
  const params: Record<string, string> = {}
  for (const [key, value] of new URLSearchParams(
    hash.startsWith('#') ? hash.slice(1) : hash
  ).entries()) {
    params[key] = value
  }
  return params
}

/**
 * Reads the panel a URL fragment names. Like the other slices, reading is the
 * app's job, done once before the service exists - it opens nothing on its own,
 * because the row behind the identity has to be found or fetched first.
 */
export function readSlideInFromHash<TRow, TIdentity>(
  descriptor: SlideInUrlDescriptor<TRow, TIdentity>,
  hash: string
): SlideInUrlState<TIdentity> | null {
  const params = parseFragment(hash)
  const identity = descriptor.decode(params)
  if (identity === null) {
    return null
  }
  return { identity, tabId: params[TAB_KEY], params }
}

export interface SlideInWriterOptions<TRow, TIdentity> {
  descriptor: SlideInUrlDescriptor<TRow, TIdentity>
  /** The listing to look for the row in before falling back to a fetch. */
  service: MonitoringService<TRow>
  /** The row the panel shows, as the page holds it. */
  current: Ref<TRow | null>
  /** The tab on show; bind the same ref into the panel as `v-model:activeTabId`. */
  tabId: Ref<string | undefined>
  /** What the URL names, from {@link readSlideInFromHash}. */
  initial: SlideInUrlState<TIdentity> | null
  open: (row: TRow) => void
  close: () => void
}

/**
 * The open detail panel as a slice of the URL fragment.
 *
 * The fragment rather than the query string because opening a panel is a
 * navigation: it gets its own history entry, so Back closes the panel and
 * returns to the listing instead of leaving the page. The query string keeps
 * carrying what the listing shows, and Back over a filter change would be a
 * different feature.
 *
 * A fragment is honoured exactly once per navigation, and only after the
 * listing has answered: a row it has is opened from the row it loaded and
 * scrolled into view, and one it does not have is fetched by identity instead.
 * Trying again on every poll would otherwise pop a panel open minutes later,
 * the moment a filtered-out row happened to match again.
 *
 * A fragment that opens nothing at all is left in the address bar untouched -
 * the user may still navigate back out of it - and logged, the way every other
 * slice logs what it had to drop.
 */
export function slideInWriter<TRow, TIdentity>(
  options: SlideInWriterOptions<TRow, TIdentity>
): UrlStateWriter {
  return new SlideInUrlSlice(options).toWriter()
}

class SlideInUrlSlice<TRow, TIdentity> {
  /** What the URL asks for, kept until it opens or the user navigates away. */
  private readonly requested: Ref<SlideInUrlState<TIdentity> | null>
  /** Whether the current request has had its one attempt. */
  private settled = false

  constructor(private readonly options: SlideInWriterOptions<TRow, TIdentity>) {
    this.requested = ref(options.initial) as Ref<SlideInUrlState<TIdentity> | null>
    watch(
      options.service.hasLoaded,
      (hasLoaded) => {
        if (hasLoaded) {
          void this.settleRequest()
        }
      },
      { immediate: true }
    )
  }

  toWriter(): UrlStateWriter {
    const { descriptor } = this.options
    return {
      name: 'slide-in',
      keys: [...descriptor.keys, TAB_KEY],
      target: 'hash',
      history: 'push',
      params: this.params(),
      apply: (params) => this.applyUrl(params)
    }
  }

  private params(): ComputedRef<Record<string, string | null>> {
    const { descriptor, current, tabId } = this.options
    return computed(() => {
      const row = current.value
      if (row !== null) {
        const tab = tabId.value
        return {
          ...descriptor.encode(row),
          [TAB_KEY]: tab === undefined || tab === descriptor.defaultTabId ? null : tab
        }
      }
      const unopened = this.requested.value
      if (unopened !== null) {
        return unopened.params
      }
      return Object.fromEntries([...descriptor.keys, TAB_KEY].map((key) => [key, null]))
    })
  }

  private applyUrl(params: Record<string, string>): void {
    const identity = this.options.descriptor.decode(params)
    if (identity === null) {
      this.requested.value = null
      this.settled = true
      this.options.close()
      return
    }
    this.requested.value = { identity, tabId: params[TAB_KEY], params }
    this.settled = false
    void this.settleRequest()
  }

  private async settleRequest(): Promise<void> {
    const { descriptor, service } = this.options
    const request = this.requested.value
    if (request === null || this.settled || !service.hasLoaded.value) {
      return
    }
    this.settled = true

    const listed = service.items.value.find((row) => descriptor.matches(row, request.identity))
    if (listed !== undefined) {
      this.adopt(request, listed)
      service.revealRow(listed)
      return
    }

    const fetched = await descriptor.load(request.identity)
    if (this.requested.value !== request) {
      return
    }
    if (fetched === null) {
      console.warn('slide-in: the URL names a row that is gone or not visible; left it closed')
      return
    }
    this.adopt(request, fetched)
  }

  private adopt(request: SlideInUrlState<TIdentity>, row: TRow): void {
    this.options.tabId.value = request.tabId
    this.options.open(row)
    this.requested.value = null
  }
}
