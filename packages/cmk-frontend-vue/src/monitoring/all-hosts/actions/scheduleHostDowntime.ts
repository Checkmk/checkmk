/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostRef } from '@/monitoring/shared/api/types'
import {
  type DowntimePresetOption,
  type DowntimeRecurrenceOption,
  type ScheduleDowntimeFormValues
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'
import { createScheduleDowntimeAction } from '@/monitoring/shared/components/action/actions/scheduleDowntime'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useScheduleHostDowntimeAction(
  recurrences: DowntimeRecurrenceOption[],
  presets: DowntimePresetOption[],
  presetsUrl: string | null
): MonitoringAction<ScheduleDowntimeFormValues, HostRef> {
  const { _t, _tn } = usei18n()

  return createScheduleDowntimeAction<HostRef>({
    submitLabel: _t('Schedule host downtime'),
    description: [
      _t('Scheduled downtimes set the hosts in planned maintenance.'),
      _t('Downtimes reduce false alarms and avoid skewed availability statistics.')
    ],
    targetKind: 'host',
    recurrences,
    presets,
    presetsUrl,
    async schedule(api, targets, values, options) {
      const hostNames = targets.map((target) => target.name)
      if (values.includeChildHosts) {
        hostNames.push(...(await api.resolveChildHosts(hostNames)))
      }
      await api.scheduleDowntime(hostNames, options)
      return hostNames.length
    },
    successMessage: (count) =>
      _tn(
        'Scheduled a downtime for %{count} host',
        'Scheduled a downtime for %{count} hosts',
        count,
        {
          count
        }
      ),
    errorMessage: _t('Could not schedule the downtime for the selected hosts.')
  })
}
