/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { ModifiedAttributesApi } from '@/monitoring/shared/api/actions/modifiedAttributes'
import type { HostRef } from '@/monitoring/shared/api/types'
import { createResetModifiedAttributesAction } from '@/monitoring/shared/components/action/actions/resetModifiedAttributes'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useResetHostModifiedAttributesAction(): MonitoringAction<
  Record<string, never>,
  HostRef
> {
  const { _t, _tn } = usei18n()
  const api = new ModifiedAttributesApi()

  return createResetModifiedAttributesAction<HostRef>({
    run: (targets) => api.resetHosts(targets),
    successMessage: (count) =>
      _tn(
        'Modified attributes are reset for the selected host',
        'Modified attributes are reset for the selected hosts',
        count
      ),
    errorHeading: _t('Could not reset the modified attributes of the selected hosts')
  })
}
