/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ServiceState } from '@/monitoring/shared/api/types'
import type { MonitoringCommandsPayload } from '@/monitoring/shared/components/action/commandsPayload'
import type { RowExportTexts } from '@/monitoring/shared/export/useRowExport'
import { type ServiceActions, useServiceActions } from '@/monitoring/shared/useServiceActions'

import type { QuickFilterConfig } from './FilterStore'

export interface ServiceListing extends ServiceActions {
  /** The quick filters offered above the service table. */
  quickFilters: QuickFilterConfig[]
  /** What the export tells the user while and after exporting services. */
  exportTexts: RowExportTexts
  /** The label of the action bar for a selection of `count` services. */
  selectionLabel: (count: number) => TranslatedString
  /** The label naming the selected and the total number of services. */
  countsLabel: (selected: number, total: number) => TranslatedString
}

export function useServiceListing(payload: MonitoringCommandsPayload): ServiceListing {
  const { _t, _tn } = usei18n()

  const quickFilters: QuickFilterConfig[] = [
    {
      label: _t('Unhandled service problems'),
      tooltip: _t(
        'Show only services in a problem state (WARN, CRIT or UNKNOWN) that are neither acknowledged nor in a scheduled downtime'
      ),
      filter: {
        type: 'and',
        children: [
          {
            type: 'condition',
            field: 'state',
            op: 'one_of',
            value: ['WARN', 'CRIT', 'UNKNOWN'] as ServiceState[]
          },
          { type: 'condition', field: 'acknowledged', op: 'eq', value: false },
          { type: 'condition', field: 'in_downtime', op: 'eq', value: false }
        ]
      }
    }
  ]

  const exportTexts: RowExportTexts = {
    exporting: _t('Exporting services…'),
    notLoaded: _t('The services could not be loaded, so nothing was exported.'),
    truncated: (counts, canShowMore) =>
      canShowMore
        ? _t(
            'Exported %{exported} of %{matched} services. Show more services to export more.',
            counts
          )
        : _t(
            'Exported %{exported} of %{matched} services. Narrow the filters to export all of them.',
            counts
          )
  }

  function selectionLabel(count: number): TranslatedString {
    return _tn('Selected service: %{count}', 'Selected services: %{count}', count, { count })
  }

  function countsLabel(selected: number, total: number): TranslatedString {
    return _tn(
      'Selected service: %{selected} | Total services: %{total}',
      'Selected services: %{selected} | Total services: %{total}',
      selected,
      { selected, total }
    )
  }

  return {
    ...useServiceActions(payload),
    quickFilters,
    exportTexts,
    selectionLabel,
    countsLabel
  }
}
