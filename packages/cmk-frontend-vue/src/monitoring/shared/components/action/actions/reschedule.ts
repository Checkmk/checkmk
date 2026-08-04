/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { RescheduleApi } from '@/monitoring/shared/api/actions/reschedule'
import type { HostRef } from '@/monitoring/shared/api/types'

import type { MonitoringAction } from '../types'
import RescheduleForm, { type RescheduleValues } from './RescheduleForm.vue'

export const RESCHEDULE_ACTION_ID = 'reschedule'

const DEFAULT_SPREAD_MINUTES = 5

export function useRescheduleAction(): MonitoringAction<RescheduleValues> {
  const { _t, _tn } = usei18n()
  const api = new RescheduleApi()

  return {
    id: RESCHEDULE_ACTION_ID,
    title: _t('Reschedule active checks'),
    submitLabel: _t('Reschedule checks'),
    description: [
      _t('Execution will be spread across custom time period to avoid network overload.')
    ],
    form: RescheduleForm,
    defaultValues: () => ({ spreadMinutes: DEFAULT_SPREAD_MINUTES }),
    perform: async (targets: HostRef[], values: RescheduleValues) => {
      try {
        const count = await api.rescheduleHosts(targets, values.spreadMinutes ?? 0)
        return {
          variant: 'success',
          message: _tn('Rescheduled %{count} check', 'Rescheduled %{count} checks', count, {
            count
          })
        }
      } catch {
        return {
          variant: 'error',
          message: _t('Could not reschedule the checks for the selected hosts.')
        }
      }
    }
  }
}
