/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { HostServicesApi } from '@/monitoring/shared/api/hostServices'
import type { ServiceRef } from '@/monitoring/shared/api/types'
import { type RescheduleValues } from '@/monitoring/shared/components/action/actions/RescheduleForm.vue'
import { createRescheduleAction } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

/** The agent-based check: its run updates every service of the host that is its byproduct. */
const AGENT_BASED_CHECK = 'Check_MK'

export function useRescheduleServicesAction(): MonitoringAction<RescheduleValues, ServiceRef> {
  const { _t } = usei18n()

  const servicesApi = new HostServicesApi()

  return createRescheduleAction<ServiceRef>({
    reschedule: (api, targets, spreadMinutes) => api.rescheduleServices(targets, spreadMinutes),
    lastCheck: async (service) =>
      (await servicesApi.fetchServiceOverview(service)).last_check ?? null,
    checkRan: ({ host, description }) =>
      description === AGENT_BASED_CHECK
        ? _t('The "Check_MK" service of %{host} has run, and with it the services it updates', {
            host: host.name
          })
        : _t('The check of "%{service}" on %{host} has run', {
            service: description,
            host: host.name
          }),
    errorHeading: _t('Could not reschedule the checks for the selected services')
  })
}
