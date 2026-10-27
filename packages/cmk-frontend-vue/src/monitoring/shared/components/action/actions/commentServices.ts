/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import type { ServiceRef } from '@/monitoring/shared/api/types'
import { type CommentValues } from '@/monitoring/shared/components/action/actions/CommentForm.vue'
import { createCommentAction } from '@/monitoring/shared/components/action/actions/comment'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

export function useCommentServicesAction(): MonitoringAction<CommentValues, ServiceRef> {
  const { _t, _tn } = usei18n()

  return createCommentAction<ServiceRef>({
    comment: (api, targets, comment) => api.commentServices(targets, comment),
    successMessage: (count) =>
      _tn(
        'Added comment to the selected service',
        'Added comments to the selected services',
        count
      ),
    errorHeading: _t('Could not add the comments to the selected services')
  })
}
