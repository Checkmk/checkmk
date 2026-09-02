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

/** Target is the service description; the host is fixed to the page's host. */
export function useAcknowledgeServicesAction(
  host: HostRef,
  links: AcknowledgeLinks,
  defaults: AcknowledgeDefaults
): MonitoringAction<AcknowledgeValues, string> {
  const { _tn } = usei18n()

  return createAcknowledgeAction<string>({
    targetKind: 'service',
    links,
    defaults,
    async acknowledge(api, targets, options) {
      await api.acknowledgeServices(host.name, targets, options)
      return targets.length
    },
    successMessage: (count) =>
      _tn(
        'Acknowledged the problem of the selected service',
        'Acknowledged the problems of the selected services',
        count
      )
  })
}
