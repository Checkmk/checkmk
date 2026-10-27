/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ServiceRef, ServiceState } from '@/monitoring/shared/api/types'
import { acknowledgeDefaults } from '@/monitoring/shared/components/action/actions/acknowledge'
import { useAcknowledgeServicesAction } from '@/monitoring/shared/components/action/actions/acknowledgeServices'
import { useCommentServicesAction } from '@/monitoring/shared/components/action/actions/commentServices'
import { useFakeServiceCheckResultsAction } from '@/monitoring/shared/components/action/actions/fakeServiceCheckResults'
import { useNotifyServicesAction } from '@/monitoring/shared/components/action/actions/notifyServices'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import { useRescheduleServicesAction } from '@/monitoring/shared/components/action/actions/rescheduleServices'
import { downtimePresets } from '@/monitoring/shared/components/action/actions/scheduleDowntime'
import { useScheduleServiceDowntimeAction } from '@/monitoring/shared/components/action/actions/scheduleServiceDowntime'
import { barActions } from '@/monitoring/shared/components/action/barActions'
import type { MonitoringCommandsPayload } from '@/monitoring/shared/components/action/commandsPayload'
import {
  type MonitoringActionRegistry,
  createActionRegistry
} from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import type { RowExportTexts } from '@/monitoring/shared/export/useRowExport'

import type { QuickFilterConfig } from './FilterStore'

export interface ServiceListing {
  /** The commands the user may run on a service, as buttons of the action bar. */
  permittedActions: CellAction[]
  /** The further commands the user may run on a service, in the action bar's "More" menu. */
  moreActions: CellAction[]
  /**
   * Whether the user may reschedule at all. What rescheduling a single service means differs per
   * service - its label, its icon and even which service the command acts on - so the row builds
   * that entry from what the backend says about the service it shows.
   */
  mayReschedule: boolean
  /**
   * Whether the selection can be acted on. Checkboxes only make sense then, so the permitted-action
   * list that decides the action bar decides the select column too.
   */
  mayActOnSelection: boolean
  /** The service commands of the action pane. */
  registry: MonitoringActionRegistry<ServiceRef>
  /** The quick filters offered above the service table. */
  quickFilters: QuickFilterConfig[]
  /** What the export tells the user while and after exporting services. */
  exportTexts: RowExportTexts
  /** The label of the action bar for a selection of `count` services. */
  selectionLabel: (count: number) => TranslatedString
  /** The label naming the selected and the total number of services. */
  countsLabel: (selected: number, total: number) => TranslatedString
}

// Actions the action bar runs immediately with their default values when exactly one service is
// selected. Only actions that are safe without user input belong here — form-based ones
// (acknowledge, downtime) carry essential input and go through the action pane instead.
export const IMMEDIATE_SERVICE_COMMAND_IDS: readonly string[] = [RESCHEDULE_ACTION_ID]

export function useServiceListing(payload: MonitoringCommandsPayload): ServiceListing {
  const { _t, _tn } = usei18n()

  const permitted: CellAction[] = (payload.actions ?? []).map((action) => ({
    id: action.ident,
    label: action.title as TranslatedString,
    icon: action.icon as SimpleIcons
  }))

  const registry = createActionRegistry<ServiceRef>([
    useAcknowledgeServicesAction(
      {
        presetsUrl: payload.acknowledge_presets_url ?? null,
        notificationRulesUrl: payload.notification_rules_url ?? null
      },
      acknowledgeDefaults(payload.acknowledge_defaults)
    ),
    useRescheduleServicesAction(),
    useScheduleServiceDowntimeAction(
      payload.downtime_recurrences ?? [],
      downtimePresets(payload.downtime_presets),
      payload.downtime_presets_url ?? null
    ),
    useCommentServicesAction(),
    useNotifyServicesAction(),
    useFakeServiceCheckResultsAction()
  ])

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

  const { bar, more } = barActions(permitted, registry)

  return {
    permittedActions: bar,
    moreActions: more,
    mayReschedule: permitted.some((action) => action.id === RESCHEDULE_ACTION_ID),
    mayActOnSelection: permitted.length > 0,
    registry,
    quickFilters,
    exportTexts,
    selectionLabel,
    countsLabel
  }
}
