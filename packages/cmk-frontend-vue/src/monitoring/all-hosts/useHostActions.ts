/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { HostRef } from '@/monitoring/shared/api/types'
import { acknowledgeDefaults } from '@/monitoring/shared/components/action/actions/acknowledge'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import { downtimePresets } from '@/monitoring/shared/components/action/actions/scheduleDowntime'
import { barActions } from '@/monitoring/shared/components/action/barActions'
import type { MonitoringCommandsPayload } from '@/monitoring/shared/components/action/commandsPayload'
import {
  type MonitoringActionRegistry,
  createActionRegistry
} from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

import { useAcknowledgeHostsAction } from './actions/acknowledgeHosts'
import { useCommentHostsAction } from './actions/commentHosts'
import { useFakeHostCheckResultsAction } from './actions/fakeHostCheckResults'
import { useNotifyHostsAction } from './actions/notifyHosts'
import { useRemoveHostAcknowledgementsAction } from './actions/removeHostAcknowledgements'
import { useRescheduleHostsAction } from './actions/rescheduleHosts'
import { useScheduleHostDowntimeAction } from './actions/scheduleHostDowntime'
import { HostActionMenuApi } from './api/actionMenu'

/** What a page sends about the host commands and the Setup links it offers. */
export interface HostActionsPayload extends MonitoringCommandsPayload {
  row_actions?: { ident: string; title: string; icon: string; url: string }[] | undefined
}

export interface HostActions {
  /** The commands the user may run on a host, as buttons of the action bar. */
  permittedActions: CellAction[]
  /** The further commands the user may run on a host, in the action bar's "More" menu. */
  moreActions: CellAction[]
  /** Buttons linking into Setup, their url keeping the `{host}` placeholder. */
  rowActions: CellAction[]
  registry: MonitoringActionRegistry
  loadActionMenu: (host: HostRef) => Promise<CellAction[]>
}

// Icons come from the command registry. Only commands whose registry icon has no counterpart in the
// Vue icon set need an entry here.
const ACTION_ICON_OVERRIDES: Record<string, SimpleIcons> = {
  [RESCHEDULE_ACTION_ID]: 'reload'
}

// Command entries the row dropdown runs immediately with their default values (no form), acting on
// that single host to mirror the legacy per-row action menu. Only list actions that are safe
// without user input — form-based ones (acknowledge, downtime) carry essential per-host input and
// must go through the action pane, not here. They carry no url, so ActionsCell emits `select`.
export const IMMEDIATE_HOST_COMMAND_IDS: readonly string[] = [RESCHEDULE_ACTION_ID]

/** The host commands, Setup links and overflow menu of every page that offers a host. */
export function useHostActions(payload: HostActionsPayload): HostActions {
  const permitted: CellAction[] = (payload.actions ?? []).map((action) => ({
    id: action.ident,
    label: action.title as TranslatedString,
    icon: ACTION_ICON_OVERRIDES[action.ident] ?? (action.icon as SimpleIcons)
  }))

  const rowActions: CellAction[] = (payload.row_actions ?? []).map((action) => ({
    id: action.ident,
    label: action.title as TranslatedString,
    icon: action.icon as SimpleIcons,
    url: action.url
  }))

  const rowCommands = permitted.filter((action) => IMMEDIATE_HOST_COMMAND_IDS.includes(action.id))

  const actionMenuApi = new HostActionMenuApi()

  // Overflow-menu entries for a host: the immediate commands (reschedule) followed by the fetched
  // legacy action-menu links (inventory, notes, topology, download, ...).
  async function loadActionMenu(host: HostRef): Promise<CellAction[]> {
    const items = await actionMenuApi.fetchActionMenu(host)
    return [
      ...rowCommands,
      ...items.map((item) => ({
        id: `${item.title}|${item.url}`,
        label: item.title as TranslatedString,
        icon: item.icon_name as SimpleIcons,
        url: item.url,
        target: item.target
      }))
    ]
  }

  const registry = createActionRegistry([
    useAcknowledgeHostsAction(
      {
        presetsUrl: payload.acknowledge_presets_url ?? null,
        notificationRulesUrl: payload.notification_rules_url ?? null
      },
      acknowledgeDefaults(payload.acknowledge_defaults)
    ),
    useRescheduleHostsAction(),
    useScheduleHostDowntimeAction(
      payload.downtime_recurrences ?? [],
      downtimePresets(payload.downtime_presets),
      payload.downtime_presets_url ?? null
    ),
    useCommentHostsAction(),
    useNotifyHostsAction(),
    useFakeHostCheckResultsAction(),
    useRemoveHostAcknowledgementsAction()
  ])

  const { bar, more } = barActions(permitted, registry)

  return { permittedActions: bar, moreActions: more, rowActions, registry, loadActionMenu }
}
