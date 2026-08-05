/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnFiltersState } from '@tanstack/vue-table'
import type { ConfiguredFilters, ConfiguredValues } from 'cmk-ui-library/components/filter'

import { COLUMN_FILTERS } from '../columns'

/**
 * Bridges the Network flow filter context with the table's column filter state.
 *
 * The header funnels edit the very same filters the bar does - the ones that
 * correspond to a column - so there is one filter model, not two. This is
 * deliberately not the shared FilterStore bridge: that one is field-centric and
 * typed to the hosts endpoint's condition union, while these values are a
 * visuals filter's HTTP variables.
 */

function isSet(values: ConfiguredValues | undefined): boolean {
  return values !== undefined && Object.values(values).some((value) => value.trim() !== '')
}

/** The column filter state the funnels should show for `context`. */
export function contextToColumnFilters(context: ConfiguredFilters): ColumnFiltersState {
  return Object.entries(COLUMN_FILTERS).flatMap(([columnId, filterId]) => {
    const values = context[filterId]
    return isSet(values) ? [{ id: columnId, value: values }] : []
  })
}

/**
 * `context` with the column-bound filters replaced by what the funnels now hold.
 *
 * Filters without a column - Time, Host - are carried over untouched: the funnels
 * know nothing about them and must not drop them.
 */
export function columnFiltersToContext(
  context: ConfiguredFilters,
  columnFilters: ColumnFiltersState
): ConfiguredFilters {
  const next: ConfiguredFilters = {}
  const columnBound = new Set(Object.values(COLUMN_FILTERS))
  for (const [filterId, values] of Object.entries(context)) {
    if (!columnBound.has(filterId)) {
      next[filterId] = values
    }
  }
  for (const [columnId, filterId] of Object.entries(COLUMN_FILTERS)) {
    const values = columnFilters.find((filter) => filter.id === columnId)?.value as
      | ConfiguredValues
      | undefined
    if (isSet(values)) {
      next[filterId] = values!
    }
  }
  return next
}
