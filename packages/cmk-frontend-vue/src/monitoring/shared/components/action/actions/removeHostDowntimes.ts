/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { RemoveDowntimeApi } from '@/monitoring/shared/api/actions/downtime'
import type { HostRef } from '@/monitoring/shared/api/types'
import { createRemoveDowntimesAction } from '@/monitoring/shared/components/action/actions/remove'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useRemoveHostDowntimesAction(): MonitoringAction<Record<string, never>, HostRef> {
  const { _t, _tn } = usei18n()
  const api = new RemoveDowntimeApi()

  return createRemoveDowntimesAction<HostRef>({
    remove: (targets) => api.removeHostDowntimes(targets.map((target) => target.name)),
    successMessage: (count) =>
      _tn(
        'Removed downtime of the selected host',
        'Removed downtimes of the selected hosts',
        count
      ),
    errorHeading: _t('Could not remove the downtimes of the selected hosts')
  })
}
