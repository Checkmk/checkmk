/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** A single checkable value shown in the {@link CheckboxListFilter} dropdown. */
export interface FilterCheckboxOption {
  value: string
  title: string
}

/**
 * Filter that presents a fixed list of checkable values with a tri-state
 * "select all" entry and an optional inline search field.
 */
export interface CheckboxListFilter {
  type: 'checkbox-list'
  options: FilterCheckboxOption[]
  /** Show the inline search field once the option count exceeds this value. */
  searchThreshold?: number
}

/**
 * Per-column filter description, injected via `columnDef.meta.filter`. The
 * `FilterDropdown` switches its rendered content on `type`.
 *
 * Future filter types (numeric range, IP range, ...) extend this union; the
 * `FilterDropdown` parent keeps owning the popover and keyboard handling while
 * each new content component only renders its own active state.
 */
export type ColumnFilterDefinition = CheckboxListFilter
