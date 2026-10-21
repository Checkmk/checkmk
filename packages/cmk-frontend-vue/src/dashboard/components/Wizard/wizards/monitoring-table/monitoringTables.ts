/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MonitoringTableContent } from '@/dashboard/types/widget'
import { DEFAULT_DISPLAY_OPTIONS } from '@/monitoring/shared/types'
import { monitoringTableRegistry } from '@/monitoring/table-widget/registry'
import type { MonitoringTableName } from '@/monitoring/table-widget/tableDescriptors'

const { _t } = usei18n()

export const DEFAULT_ROW_LIMIT = 1000

export interface MonitoringTableView {
  title: TranslatedString
  infos: string[]
}

/** The tables the wizard lets the user choose from. */
export const OFFERED_TABLES: readonly MonitoringTableName[] = ['hosts']

export function monitoringTableViews(): Record<MonitoringTableName, MonitoringTableView> {
  return {
    hosts: { title: _t('All hosts'), infos: ['host'] }
  }
}

/** The active filters the view of `table` cannot apply, as they filter another object type. */
export function filtersForeignTo(
  table: MonitoringTableName,
  activeFilters: readonly string[],
  infoOf: (filterId: string) => string | undefined
): string[] {
  const { infos } = monitoringTableViews()[table]
  return activeFilters.filter((filterId) => !infos.includes(infoOf(filterId) ?? ''))
}

export function defaultMonitoringTableContent(table: MonitoringTableName): MonitoringTableContent {
  return {
    type: 'monitoring_table',
    table,
    columns: monitoringTableRegistry
      .descriptor(table)
      .catalog()
      .filter((column) => column.shownByDefault)
      .map((column) => column.id),
    sort: [],
    limit: DEFAULT_ROW_LIMIT,
    date_format: DEFAULT_DISPLAY_OPTIONS.dateFormat,
    timestamp_format: DEFAULT_DISPLAY_OPTIONS.timestampFormat
  }
}
