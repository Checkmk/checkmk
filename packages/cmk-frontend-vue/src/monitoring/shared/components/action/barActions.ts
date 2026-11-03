/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

import { ACK_ACTION_ID } from './actions/acknowledge'
import { RESCHEDULE_ACTION_ID } from './actions/reschedule'
import { SCHEDULE_DOWNTIME_ACTION_ID } from './actions/scheduleDowntime'
import type { MonitoringActionRegistry } from './registry'

/** The commands the action bar shows as buttons; every other one goes to its "More" menu. */
const BAR_ACTION_IDS: readonly string[] = [
  ACK_ACTION_ID,
  SCHEDULE_DOWNTIME_ACTION_ID,
  RESCHEDULE_ACTION_ID
]

export interface BarActions {
  bar: CellAction[]
  more: CellAction[]
}

/**
 * Splits the permitted commands into the bar's buttons and its "More" menu. A command the page
 * does not implement yet stays in the menu, disabled, so the user sees what is coming.
 */
export function barActions<Target>(
  permitted: CellAction[],
  registry: MonitoringActionRegistry<Target>
): BarActions {
  const { _t } = usei18n()
  return {
    bar: permitted.filter((action) => BAR_ACTION_IDS.includes(action.id)),
    more: permitted
      .filter((action) => !BAR_ACTION_IDS.includes(action.id))
      .map((action) =>
        action.id in registry
          ? action
          : { ...action, disabled: true, tooltip: _t('Not available yet') }
      )
  }
}
