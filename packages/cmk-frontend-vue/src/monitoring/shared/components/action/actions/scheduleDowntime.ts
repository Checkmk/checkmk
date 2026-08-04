/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { ScheduleDowntimeApi } from '@/monitoring/shared/api/actions/downtime'
import type { HostRef } from '@/monitoring/shared/api/types'

import type { MonitoringAction } from '../types'
import ScheduleDowntimeForm, {
  type ScheduleDowntimeFormValues,
  defaultScheduleDowntimeValues,
  downtimeWindow
} from './ScheduleDowntimeForm.vue'

export const SCHEDULE_DOWNTIME_ACTION_ID = 'schedule_downtimes'

export function useScheduleDowntimeAction(): MonitoringAction<ScheduleDowntimeFormValues> {
  const { _t, _tn } = usei18n()
  const api = new ScheduleDowntimeApi()

  return {
    id: SCHEDULE_DOWNTIME_ACTION_ID,
    title: _t('Schedule downtimes'),
    submitLabel: _t('Schedule host downtime'),
    description: [
      _t('Scheduled downtimes set the hosts in planned maintenance.'),
      _t('Downtimes reduce false alarms and avoid skewed availability statistics.')
    ],
    form: ScheduleDowntimeForm,
    defaultValues: defaultScheduleDowntimeValues,
    perform: async (targets: HostRef[], values: ScheduleDowntimeFormValues) => {
      const window = downtimeWindow(values)
      if (window === null) {
        return {
          variant: 'error',
          message: _t('Please choose a downtime duration greater than zero.')
        }
      }
      try {
        const hostNames = targets.map((target) => target.name)
        if (values.includeChildHosts) {
          hostNames.push(...(await api.resolveChildHosts(hostNames)))
        }
        const durationMinutes = values.flexible
          ? Math.round((new Date(window.end).getTime() - new Date(window.start).getTime()) / 60_000)
          : 0
        await api.scheduleDowntime(hostNames, {
          comment: values.comment.trim(),
          startTime: window.start,
          endTime: window.end,
          durationMinutes
        })
        const count = hostNames.length
        return {
          variant: 'success',
          message: _tn(
            'Scheduled a downtime for %{count} host',
            'Scheduled a downtime for %{count} hosts',
            count,
            { count }
          )
        }
      } catch {
        return {
          variant: 'error',
          message: _t('Could not schedule the downtime for the selected hosts.')
        }
      }
    }
  }
}
