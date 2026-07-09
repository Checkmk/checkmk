/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterField } from '@/monitoring/shared/api/types'

/** A single checkable value shown in the {@link CheckboxListFilter} dropdown. */
export interface FilterCheckboxOption {
  value: string
  title: string
}

/**
 * Filter that presents a fixed list of checkable values with a tri-state
 * "select all" entry and an optional inline search field.
 *
 * The v-model value is a `ColumnFilterNode<F>` so the column filter state
 * stores a typed condition directly — no `filterToNode` translation needed.
 */
export interface CheckboxListFilter<F extends FilterField = FilterField> {
  type: 'checkbox-list'
  /** API field this filter targets. Used to produce the correct condition node. */
  field: F
  options: FilterCheckboxOption[]
  /** Show the inline search field once the option count exceeds this value. */
  searchThreshold?: number
}
export interface StringInputFilter<F extends FilterField = FilterField> {
  type: 'string-input'
  /** API field this filter targets. Used to produce the correct condition node. */
  field: F
}

/**
 * Filter that matches an integer field against a closed/open range. The lower
 * and upper bounds map onto `gte` / `lte` numeric conditions; supplying both
 * produces an `and` of the two, a single bound a lone condition.
 *
 * The v-model value is a `ColumnFilterNode<F>` so the column filter state stores
 * a typed condition directly — no `filterToNode` translation needed.
 */
export interface NumericFilter<F extends FilterField = FilterField> {
  type: 'numeric'
  /** API field this filter targets. Used to produce the correct condition node. */
  field: F
  /** Optional unit suffix shown after the upper-bound field (e.g. "services"). */
  unit?: string
}

/** A single boolean field shown as a tri-state radio group in a {@link BooleanGroupFilter}. */
export interface BooleanFilterGroup<F extends FilterField = FilterField> {
  /** Boolean API field this group targets (e.g. `in_downtime`, `acknowledged`). */
  field: F
  /** Label shown above the group's radio buttons. */
  title: string
}

/**
 * Filter that presents one tri-state radio group per boolean field. Each group
 * offers "both" (no condition), "has to be true" and "has to be false". A group
 * left on "both" contributes nothing; the remaining groups produce `eq` boolean
 * conditions that are AND-combined into the column filter node.
 *
 * The v-model value is a `ColumnFilterNode<F>` so the column filter state stores
 * a typed condition directly — no `filterToNode` translation needed.
 */
export interface BooleanGroupFilter<F extends FilterField = FilterField> {
  type: 'boolean-group'
  groups: BooleanFilterGroup<F>[]
}

/**
 * Per-column filter description, injected via `columnDef.meta.filter`. The
 * `FilterDropdown` switches its rendered content on `type`.
 *
 * Future filter types (numeric range, IP range, ...) extend this union; the
 * `FilterDropdown` parent keeps owning the popover and keyboard handling while
 * each new content component only renders its own active state.
 */
export type ColumnFilterDefinition<F extends FilterField = FilterField> =
  | CheckboxListFilter<F>
  | StringInputFilter<F>
  | NumericFilter<F>
  | BooleanGroupFilter<F>

/**
 * The API field(s) a column filter targets: single-field filters expose one,
 * a boolean group one per group. Centralised alongside the filter definitions
 * so consumers (e.g. the column-filter bridge) stay generic and never switch on
 * a concrete filter shape — a new filter type extends this one function.
 */
export function filterFields(filter: ColumnFilterDefinition): FilterField[] {
  return 'groups' in filter ? filter.groups.map((group) => group.field) : [filter.field]
}
