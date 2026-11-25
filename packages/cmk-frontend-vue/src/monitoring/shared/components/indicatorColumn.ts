/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, computed, h, ref, watchEffect } from 'vue'

import type { CustomIcon, FilterField } from '@/monitoring/shared/api/types'
import { columnId } from '@/monitoring/shared/tableState/schema'

import { CELL_PADDING } from './MonitoringTableContext'
import type { BooleanGroupFilter } from './filter/types'
import { iconListWidth } from './iconList'
import { type RowWithStateIcons, indicatorModes } from './stateColumn'

/** The Indicator column. */
export const INDICATOR_COLUMN_ID = 'indicator'

export const MODE_ICONS_PER_ROW = 3

export const INDICATOR_COLUMN_MIN_WIDTH = 56
export const INDICATOR_COLUMN_MAX_WIDTH = 152
export const FILLED_INDICATOR_COLUMN_WIDTH = iconListWidth(MODE_ICONS_PER_ROW) + CELL_PADDING

export interface RowWithModes extends RowWithStateIcons {
  custom_icons?: readonly CustomIcon[] | null | undefined
}

/** The custom icons of a row the Indicator column shows: those without an action. */
export function indicatorIcons(row: RowWithModes): CustomIcon[] {
  return (row.custom_icons ?? []).filter((icon) => icon.url === undefined)
}

export function useIndicatorColumnWidth(rows: () => readonly RowWithModes[]): ComputedRef<number> {
  const carriesIndicators = ref(false)

  watchEffect(() => {
    if (rows().some((row) => indicatorModes(row.modes).length + indicatorIcons(row).length > 0)) {
      carriesIndicators.value = true
    }
  })

  return computed(() =>
    carriesIndicators.value ? FILLED_INDICATOR_COLUMN_WIDTH : INDICATOR_COLUMN_MIN_WIDTH
  )
}

/**
 * The Indicator column: the modes of a row and its custom icons without an action. It is off by
 * default unless custom icons are configured at all.
 */
export function indicatorColumn<Row extends RowWithModes, Field extends FilterField>(
  filter: BooleanGroupFilter<Field>,
  showIndicators: boolean
): ColumnDef<Row> {
  const { _t } = usei18n()
  const label = _t('Indicator')
  return {
    // The column filter bridge keys filters by accessorKey. Rows have no such field: the cells
    // read the modes themselves.
    accessorKey: INDICATOR_COLUMN_ID,
    header: () => h(CmkIcon, { name: 'icons', size: 'medium', title: label }),
    enableSorting: false,
    meta: {
      justify: 'left',
      filter,
      headerTitle: label,
      pickerLabel: label,
      hidden: !showIndicators
    }
  }
}

export function sizeIndicatorColumn<T>(columns: ColumnDef<T>[], width: number): ColumnDef<T>[] {
  return columns.map((column) =>
    columnId(column) === INDICATOR_COLUMN_ID
      ? {
          ...column,
          minSize: Math.max(INDICATOR_COLUMN_MIN_WIDTH, width),
          maxSize: INDICATOR_COLUMN_MAX_WIDTH,
          meta: { ...column.meta, fitHeader: true }
        }
      : column
  )
}
