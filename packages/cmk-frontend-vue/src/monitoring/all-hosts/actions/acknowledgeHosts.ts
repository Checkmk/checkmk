/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostRef } from '@/monitoring/shared/api/types'
import { type AcknowledgeValues } from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'
import {
  type AcknowledgeDefaults,
  type AcknowledgeLinks,
  createAcknowledgeAction
} from '@/monitoring/shared/components/action/actions/acknowledge'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useAcknowledgeHostsAction(
  links: AcknowledgeLinks,
  defaults: AcknowledgeDefaults
): MonitoringAction<AcknowledgeValues, HostRef> {
  const { _tn } = usei18n()

  return createAcknowledgeAction<HostRef>({
    targetKind: 'host',
    links,
    defaults,
    async acknowledge(api, targets, options) {
      const hostNames = targets.map((target) => target.name)
      await api.acknowledgeHosts(hostNames, options)
      return hostNames.length
    },
    successMessage: (count) =>
      _tn(
        'Acknowledged the problem for %{count} host',
        'Acknowledged the problem for %{count} hosts',
        count,
        { count }
      )
  })
}
