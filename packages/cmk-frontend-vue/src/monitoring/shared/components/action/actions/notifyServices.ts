/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { ServiceRef } from '@/monitoring/shared/api/types'
import { type CustomNotificationValues } from '@/monitoring/shared/components/action/actions/CustomNotificationForm.vue'
import { createCustomNotificationAction } from '@/monitoring/shared/components/action/actions/customNotification'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useNotifyServicesAction(): MonitoringAction<CustomNotificationValues, ServiceRef> {
  const { _t, _tn } = usei18n()

  return createCustomNotificationAction<ServiceRef>({
    targetKind: 'service',
    notify: (api, targets, options) => api.notifyServices(targets, options),
    successMessage: (count) =>
      _tn(
        'Sent custom notifications for the selected service',
        'Sent custom notifications for the selected services',
        count
      ),
    errorHeading: _t('Could not send the custom notifications for the selected services')
  })
}
