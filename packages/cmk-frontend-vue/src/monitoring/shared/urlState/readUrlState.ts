/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UrlStateFormat } from './types'

/**
 * Decodes and reconciles one slice out of `search`, logging whatever
 * reconciliation had to drop or sanitise; nothing is surfaced to the user.
 *
 * The URL is a one-way seed plus mirror, never a live binding: this runs
 * exactly once, before the service exists, and from then on {@link useUrlSync}
 * only ever writes. Nothing in monitoring/ or network-flow/ listens for
 * `popstate`, so the address bar never becomes an input again for the rest of
 * the page's life. That is deliberate - a live binding would re-derive
 * `columnVisibility` from the URL on every navigation instead of writing a
 * half-seeded map to storage - but it has two consequences worth knowing:
 *
 * - Read (here) and write ({@link useUrlSync}) are separate code paths.
 *   Nothing asserts they round-trip; each codec's own tests pin that down.
 * - Any future in-app navigation between listings (no full page load) will
 *   need this re-run explicitly - there is no hook for that today.
 */
export function readUrlState<TState, TRaw>(
  format: UrlStateFormat<TState, TRaw>,
  search: string
): TState {
  const { state, problems } = format.reconcile(format.codec.decode(new URLSearchParams(search)))
  for (const problem of problems) {
    console.warn(`${format.name}: ${problem.message}`)
  }
  return state
}
