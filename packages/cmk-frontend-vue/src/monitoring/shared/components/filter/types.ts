/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredValues } from 'cmk-ui-library/components/filter'

import type { ColumnFilterNode, FilterField } from '@/monitoring/shared/api/types'

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
  /**
   * Turns the plain text field into a chip autocomplete over this source. A
   * column that knows what values exist (labels, tags, contact groups) offers
   * them; one that does not stays a free-text field.
   */
  suggest?: (query: string) => Promise<string[]>
  /** Ask `suggest` with an empty query on focus, to seed the list. */
  suggestWhenEmpty?: boolean
  /** Pick `key:value` pairs in two steps: first the key, then that key's values. */
  keyValue?: boolean
  /** Offer what was typed with a trailing `*` as the first entry. */
  wildcardOption?: boolean
  /** Refuse further picks once this many are selected. Unbounded when unset. */
  maxSelected?: number
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

/**
 * Filter that matches a timestamp field against a closed/open range of instants, each picked
 * with a `CmkDateTimePicker`. The lower and upper bounds map onto `gte` / `lte` conditions
 * carrying unix timestamps; supplying both produces an `and` of the two, a single bound a lone
 * condition.
 *
 * The v-model value is a `ColumnFilterNode<F>` so the column filter state stores a typed condition
 * directly — no `filterToNode` translation needed.
 */
export interface DateTimeRangeFilter<F extends FilterField = FilterField> {
  type: 'date-time-range'
  /** API field this filter targets. Used to produce the correct condition node. */
  field: F
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
 * Filter that presents a {@link CheckboxListFilter}'s fixed list of checkable
 * values together with one or more boolean flags, each rendered as a
 * {@link BooleanGroupFilter}-style tri-state radio group below the checkbox
 * list. Used for the state column, whose filter combines the state enum with
 * orthogonal flags (flapping, stale) that used to live in a separate column.
 *
 * The v-model value is a `ColumnFilterNode<F | BF>` — the checkbox list's
 * `one_of` condition and any active flag `eq` condition(s), AND-combined when
 * more than one is active.
 */
export interface CheckboxListWithFlagsFilter<
  F extends FilterField = FilterField,
  BF extends FilterField = FilterField
> {
  type: 'checkbox-list-with-flags'
  /** API field the checkbox list targets. */
  field: F
  options: FilterCheckboxOption[]
  /** Show the inline search field once the option count exceeds this value. */
  searchThreshold?: number
  /** Boolean flags shown below the checkbox list, each as a tri-state radio group. */
  flags: BooleanFilterGroup<BF>[]
}

/**
 * Filter over the values of a field only the server knows, picked as chips
 * against one of the registered autocompleters. Its value is a single `one_of`
 * condition, which is what the label, tag and contact-group conditions accept.
 */
export interface AutocompleteChoiceFilter<F extends FilterField = FilterField> {
  type: 'autocomplete-choice'
  /** API field this filter targets. Used to produce the correct condition node. */
  field: F
  /** Suggestions for what has been typed so far. */
  suggest: (query: string) => Promise<string[]>
  /** Ask `suggest` with an empty query on focus, to seed the list. */
  suggestWhenEmpty?: boolean
  /** Pick `key:value` pairs in two steps: first the key, then that key's values. */
  keyValue?: boolean
  /** Offer what was typed with a trailing `*` as the first entry. */
  wildcardOption?: boolean
  /** Refuse further picks once this many are selected. Unbounded when unset. */
  maxSelected?: number
}

export interface ColumnVisibilityFilter {
  type: 'column-visibility'
}

/**
 * Filter whose content is a registered visuals filter - one of the `Filter`
 * subclasses the REST API serves under /domain-types/visual_filter - rendered
 * from that filter's own definition.
 *
 * Unlike the other variants this carries no `field`: its value is the filter's
 * `ConfiguredValues`, keyed by the filter's own HTTP variables, rather than a
 * condition on a column. A page using it therefore owns the mapping from column
 * to filter and does not go through the FilterStore.
 */
export interface VisualFilterColumnFilter {
  type: 'visual-filter'
  /** Ident of the registered filter whose definition the funnel renders. */
  filterId: string
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
  | DateTimeRangeFilter<F>
  | BooleanGroupFilter<F>
  | CheckboxListWithFlagsFilter<F>
  | AutocompleteChoiceFilter<F>
  | ColumnVisibilityFilter
  | VisualFilterColumnFilter

/**
 * The API field(s) a column filter targets: single-field filters expose one,
 * a boolean group one per group. Centralised alongside the filter definitions
 * so consumers (e.g. the column-filter bridge) stay generic and never switch on
 * a concrete filter shape — a new filter type extends this one function.
 */
export function filterFields(filter: ColumnFilterDefinition): FilterField[] {
  const fields: FilterField[] = []
  if ('field' in filter) {
    fields.push(filter.field)
  }
  if ('groups' in filter) {
    fields.push(...filter.groups.map((group) => group.field))
  }
  if ('flags' in filter) {
    fields.push(...filter.flags.map((flag) => flag.field))
  }
  return fields
}

/**
 * The committed value of a column funnel: a typed condition for the
 * field-centric variants, or a visuals filter's configured values for
 * {@link VisualFilterColumnFilter}.
 */
export type ColumnFilterValue<F extends FilterField = FilterField> =
  | ColumnFilterNode<F>
  | ConfiguredValues
