/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostRef } from '@/monitoring/shared/api/types'
import { type RescheduleValues } from '@/monitoring/shared/components/action/actions/RescheduleForm.vue'
import { createRescheduleAction } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useRescheduleHostsAction(): MonitoringAction<RescheduleValues, HostRef> {
  const { _t } = usei18n()

  return createRescheduleAction<HostRef>({
    reschedule: (api, targets, spreadMinutes) => api.rescheduleHosts(targets, spreadMinutes),
    errorMessage: _t('Could not reschedule the checks for the selected hosts.')
  })
}
