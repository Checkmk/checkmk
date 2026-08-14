/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ComputedRef } from 'vue'

/** A reconciliation rule dropped, clamped or sanitised something; carries enough to log it. */
export interface Problem<TDimension extends string = string> {
  /** Which part of the state the rule acted on, where a slice tells its parts apart. */
  dimension?: TDimension
  message: string
}

/**
 * Translates one URL-owned slice of state to and from query parameters.
 * `null` means "omit this key" - either it is at its default, or unset.
 */
export interface UrlStateCodec<TState, TRaw> {
  encode(state: TState): Record<string, string | null>
  decode(params: URLSearchParams): TRaw
}

/**
 * How one slice of state is spelled in the URL: the params it claims, the
 * codec translating them, and the reconciler deciding what survives a stale or
 * hand-edited link. Plain data throughout - the read path runs before any
 * service exists, and the DOM-facing half is {@link UrlStateWriter}.
 */
export interface UrlStateFormat<TState, TRaw> {
  /** Prefixes this slice's log lines and names it in an ownership clash. */
  readonly name: string
  /** Every param the slice claims. Two slices may not claim the same one. */
  readonly keys: readonly string[]
  readonly codec: UrlStateCodec<TState, TRaw>
  reconcile(raw: TRaw): { state: TState; problems: Problem[] }
}

/**
 * Which half of the URL a slice owns. The two are separate namespaces: the same
 * param name in the query and in the fragment is not a clash.
 */
export type UrlStateTarget = 'query' | 'hash'

/**
 * A slice as {@link useUrlSync} sees it: a claim on some params, plus what
 * they should say right now. Deliberately state-agnostic - the one thing the
 * owner of `window.history` must not need is knowledge of what a slice means.
 *
 * `params` may name a key outside `keys`: a slice whose vocabulary is only
 * known at runtime - the flow explorer's filter variables come from
 * definitions the REST API serves - cannot enumerate it up front. What it
 * wrote last flush is tracked for it, so a param it stops writing still gets
 * dropped from the URL.
 */
export interface UrlStateWriter {
  readonly name: string
  readonly keys: readonly string[]
  readonly params: ComputedRef<Record<string, string | null>>
  /** Defaults to `'query'`. */
  readonly target?: UrlStateTarget
  /**
   * `'push'` gives the change its own history entry, so Back undoes it;
   * `'replace'` (the default) rewrites the current one. Adjusting the listing
   * you are already looking at is not a navigation - opening a detail panel is.
   */
  readonly history?: 'push' | 'replace'
  /**
   * Called when the user navigates the history, with this slice's params as the
   * URL now spells them. A slice without it is write-only: Back and Forward
   * change the address bar and nothing else.
   */
  readonly apply?: (params: Record<string, string>) => void
}
