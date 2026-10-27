/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { AcknowledgeApi } from '@/monitoring/shared/api/actions/acknowledge'
import type { HostRef } from '@/monitoring/shared/api/types'
import { createRemoveAcknowledgementsAction } from '@/monitoring/shared/components/action/actions/remove'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useRemoveHostAcknowledgementsAction(): MonitoringAction<
  Record<string, never>,
  HostRef
> {
  const { _t, _tn } = usei18n()
  const api = new AcknowledgeApi()

  return createRemoveAcknowledgementsAction<HostRef>({
    remove: (targets) => api.removeHostAcknowledgements(targets.map((target) => target.name)),
    successMessage: (count) =>
      _tn(
        'Removed acknowledgement of the selected host',
        'Removed acknowledgements of the selected hosts',
        count
      ),
    errorHeading: _t('Could not remove the acknowledgements of the selected hosts')
  })
}
