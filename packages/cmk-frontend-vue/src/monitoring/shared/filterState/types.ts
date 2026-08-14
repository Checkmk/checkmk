/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterField, FilterNode } from '@/monitoring/shared/api/types'

/**
 * A table's row-narrowing state, as it should apply right now. Unlike the
 * sibling `tableState` module's `TableState`, a URL carrying this is never a
 * complete snapshot on its own - the point is exactly that it narrows what a
 * shared link shows.
 */
export interface FilterUrlState {
  filter: FilterNode | undefined
  /** The applied (submitted) search text, never a live, uncommitted keystroke. */
  search: string
}

/**
 * A {@link FilterUrlState} as decoded straight from a URL, before reconciliation
 * has dropped whatever no longer applies - a malformed filter, or one naming a
 * field this table does not offer. `filter: unknown` because a decoded value's
 * shape is unverified until reconciled against a {@link FilterUrlSchema}.
 */
export interface RawFilterUrlState {
  filter: unknown
  search: string
}

/** What a table's filter vocabulary needs to validate a decoded filter. */
export interface FilterUrlSchema {
  /** Fields any column's filter definition targets. */
  filterableFields: ReadonlySet<FilterField>
}

export type { Problem } from '@/monitoring/shared/urlState/types'
