/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { columnId } from './tableState/schema'
import type { TimestampFormatId } from './types'

export interface TimestampLabel {
  label: TranslatedString
  title?: TranslatedString
}

export interface TimestampLabels {
  lastCheck: TimestampLabel
  lastStateChange: TimestampLabel
}

export function timestampLabels(format: TimestampFormatId): TimestampLabels {
  const { _t } = usei18n()
  if (format === 'rel') {
    return {
      lastCheck: { label: _t('Check age'), title: _t('Age of the check') },
      lastStateChange: { label: _t('State age'), title: _t('Age of the state') }
    }
  }
  return {
    lastCheck: { label: _t('Last check') },
    lastStateChange: { label: _t('Last state change') }
  }
}

export function withTimestampHeaders<T>(
  columns: ColumnDef<T>[],
  format: TimestampFormatId
): ColumnDef<T>[] {
  const labels = timestampLabels(format)
  const byColumn: Record<string, TimestampLabel> = {
    last_check: labels.lastCheck,
    last_state_change: labels.lastStateChange
  }
  return columns.map((column) => {
    const label = byColumn[columnId(column) ?? '']
    if (label === undefined) {
      return column
    }
    const { headerTitle: _replaced, ...meta } = column.meta ?? {}
    return {
      ...column,
      header: label.label,
      meta: label.title === undefined ? meta : { ...meta, headerTitle: label.title }
    }
  })
}
