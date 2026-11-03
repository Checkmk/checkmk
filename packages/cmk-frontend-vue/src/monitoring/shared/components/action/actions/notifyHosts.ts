/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostRef } from '@/monitoring/shared/api/types'
import { type CustomNotificationValues } from '@/monitoring/shared/components/action/actions/CustomNotificationForm.vue'
import { createCustomNotificationAction } from '@/monitoring/shared/components/action/actions/customNotification'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useNotifyHostsAction(): MonitoringAction<CustomNotificationValues, HostRef> {
  const { _t, _tn } = usei18n()

  return createCustomNotificationAction<HostRef>({
    targetKind: 'host',
    notify: (api, targets, options) => api.notifyHosts(targets, options),
    successMessage: (count) =>
      _tn(
        'Sent custom notifications for the selected host',
        'Sent custom notifications for the selected hosts',
        count
      ),
    errorHeading: _t('Could not send the custom notifications for the selected hosts')
  })
}
