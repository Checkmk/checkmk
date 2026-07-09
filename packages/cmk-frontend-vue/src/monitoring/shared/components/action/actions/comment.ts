/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

import type { HostRef } from '@/monitoring/shared/api/types'

import type { MonitoringAction } from '../types'
import CommentForm, { type CommentValues } from './CommentForm.vue'

export const COMMENT_ACTION_ID = 'comment'

export function useCommentAction(): MonitoringAction<CommentValues> {
  const { _t, _tn } = usei18n()

  return {
    id: COMMENT_ACTION_ID,
    title: _t('Add comment'),
    submitLabel: _t('Add comment'),
    subtitle: (count) => _tn('%{count} selected host', '%{count} selected hosts', count, { count }),
    form: CommentForm,
    defaultValues: () => ({ comment: '' }),
    perform: async (targets: HostRef[]) => ({
      variant: 'success',
      message: _tn(
        'Added a comment to %{count} host',
        'Added a comment to %{count} hosts',
        targets.length,
        { count: targets.length }
      )
    })
  }
}
