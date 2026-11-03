/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { ServiceRef } from '@/monitoring/shared/api/types'
import { type FakeCheckResultValues } from '@/monitoring/shared/components/action/actions/FakeCheckResultForm.vue'
import { createFakeCheckResultAction } from '@/monitoring/shared/components/action/actions/fakeCheckResult'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useFakeServiceCheckResultsAction(): MonitoringAction<
  FakeCheckResultValues,
  ServiceRef
> {
  const { _t, _tn } = usei18n()

  return createFakeCheckResultAction<ServiceRef>({
    targetKind: 'service',
    fake: (api, targets, options) => api.fakeServices(targets, options),
    successMessage: (count) =>
      _tn(
        'Faked check result for the selected service',
        'Faked check results for the selected services',
        count
      ),
    errorHeading: _t('Could not fake the check results for the selected services')
  })
}
