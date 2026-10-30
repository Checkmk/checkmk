/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { ServiceActionMenuApi } from '@/monitoring/shared/api/serviceActionMenu'
import type { HostRef, ServiceRef } from '@/monitoring/shared/api/types'
import { acknowledgeDefaults } from '@/monitoring/shared/components/action/actions/acknowledge'
import { useAcknowledgeServicesAction } from '@/monitoring/shared/components/action/actions/acknowledgeServices'
import { useArchiveServiceHostEventsAction } from '@/monitoring/shared/components/action/actions/archiveServiceHostEvents'
import { useCommentServicesAction } from '@/monitoring/shared/components/action/actions/commentServices'
import { useFakeServiceCheckResultsAction } from '@/monitoring/shared/components/action/actions/fakeServiceCheckResults'
import { useNotifyServicesAction } from '@/monitoring/shared/components/action/actions/notifyServices'
import { useRemoveServiceAcknowledgementsAction } from '@/monitoring/shared/components/action/actions/removeServiceAcknowledgements'
import { useRemoveServiceDowntimesAction } from '@/monitoring/shared/components/action/actions/removeServiceDowntimes'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import { useRescheduleServicesAction } from '@/monitoring/shared/components/action/actions/rescheduleServices'
import { useResetServiceModifiedAttributesAction } from '@/monitoring/shared/components/action/actions/resetServiceModifiedAttributes'
import { downtimePresets } from '@/monitoring/shared/components/action/actions/scheduleDowntime'
import { useScheduleServiceDowntimeAction } from '@/monitoring/shared/components/action/actions/scheduleServiceDowntime'
import { useToggleServiceAttributesActions } from '@/monitoring/shared/components/action/actions/toggleServiceAttributes'
import { barActions } from '@/monitoring/shared/components/action/barActions'
import type { MonitoringCommandsPayload } from '@/monitoring/shared/components/action/commandsPayload'
import {
  type MonitoringActionRegistry,
  createActionRegistry
} from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

export interface ServiceActions {
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
  /** The legacy action-menu links of a service (graphs, log file viewer, custom actions, ...). */
  loadActionMenu: (host: HostRef, service: string) => Promise<CellAction[]>
}

// Actions the action bar runs immediately with their default values when exactly one service is
// selected. Only actions that are safe without user input belong here — form-based ones
// (acknowledge, downtime) carry essential input and go through the action pane instead.
export const IMMEDIATE_SERVICE_COMMAND_IDS: readonly string[] = [RESCHEDULE_ACTION_ID]

/** The service commands and overflow menu of every page that offers a service. */
export function useServiceActions(payload: MonitoringCommandsPayload): ServiceActions {
  const permitted: CellAction[] = (payload.actions ?? []).map((action) => ({
    id: action.ident,
    label: action.title as TranslatedString,
    icon: action.icon as SimpleIcons
  }))

  const actionMenuApi = new ServiceActionMenuApi()

  async function loadActionMenu(host: HostRef, service: string): Promise<CellAction[]> {
    const items = await actionMenuApi.fetchActionMenu(host, service)
    return items.map((item) => ({
      id: `${item.title}|${item.url}`,
      label: item.title as TranslatedString,
      icon: item.icon_name as SimpleIcons,
      url: item.url,
      target: item.target,
      ident: item.ident
    }))
  }

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
    useFakeServiceCheckResultsAction(),
    useRemoveServiceAcknowledgementsAction(),
    useRemoveServiceDowntimesAction(),
    ...useToggleServiceAttributesActions(),
    useResetServiceModifiedAttributesAction(),
    useArchiveServiceHostEventsAction()
  ])

  const { bar, more } = barActions(permitted, registry)

  return {
    permittedActions: bar,
    moreActions: more,
    mayReschedule: permitted.some((action) => action.id === RESCHEDULE_ACTION_ID),
    mayActOnSelection: permitted.length > 0,
    registry,
    loadActionMenu
  }
}
