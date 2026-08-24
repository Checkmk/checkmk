/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostRef } from '@/monitoring/shared/api/types'
import {
  type DowntimeRecurrenceOption,
  type ScheduleDowntimeFormValues
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'
import { createScheduleDowntimeAction } from '@/monitoring/shared/components/action/actions/scheduleDowntime'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

/** Target is the service description; the host is fixed to the page's host. */
export function useScheduleServiceDowntimeAction(
  host: HostRef,
  recurrences: DowntimeRecurrenceOption[],
  presetsUrl: string | null
): MonitoringAction<ScheduleDowntimeFormValues, string> {
  const { _t, _tn } = usei18n()

  return createScheduleDowntimeAction<string>({
    submitLabel: _t('Schedule service downtime'),
    description: [
      _t('Scheduled downtimes set the services in planned maintenance.'),
      _t('Downtimes reduce false alarms and avoid skewed availability statistics.')
    ],
    targetKind: 'service',
    recurrences,
    presetsUrl,
    async schedule(api, targets, _values, options) {
      await api.scheduleServiceDowntime(host.name, targets, options)
      return targets.length
    },
    successMessage: (count) =>
      _tn(
        'Scheduled a downtime for %{count} service',
        'Scheduled a downtime for %{count} services',
        count,
        { count }
      ),
    errorMessage: _t('Could not schedule the downtime for the selected services.')
  })
}
