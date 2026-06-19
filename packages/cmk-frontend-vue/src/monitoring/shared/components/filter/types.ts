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
 * A quick-pick chip for a {@link NumericFilter}, e.g. "Any" (1 to ∞) or "None"
 * (0 to 0). Selecting one prefills the range inputs with its bounds so the user
 * sees the resulting range before applying; selecting the active chip again
 * clears the range.
 */
export interface NumericPreset {
  label: string
  from?: number
  to?: number
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
  /**
   * Optional quick-pick chips shown above the range. Omit for a plain range;
   * not every numeric column has a meaningful preset (e.g. total service count
   * has no natural "none").
   */
  presets?: NumericPreset[]
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
