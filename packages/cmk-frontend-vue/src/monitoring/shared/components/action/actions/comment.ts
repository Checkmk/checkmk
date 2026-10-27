/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { CommentApi } from '@/monitoring/shared/api/actions/comment'

import type { MonitoringAction } from '../types'
import CommentForm, { type CommentValues } from './CommentForm.vue'
import { commandFailed } from './feedback'

export const COMMENT_ACTION_ID = 'add_comment'

export interface CommentKindConfig<Target> {
  comment(api: CommentApi, targets: Target[], comment: string): Promise<void>
  successMessage(count: number): TranslatedString
  errorHeading: TranslatedString
}

/** Shared comment flow for hosts and services: only the API call and wording differ. */
export function createCommentAction<Target>(
  config: CommentKindConfig<Target>
): MonitoringAction<CommentValues, Target> {
  const { _t } = usei18n()
  const api = new CommentApi()

  return {
    id: COMMENT_ACTION_ID,
    title: _t('Add comment'),
    submitLabel: _t('Add comment'),
    form: CommentForm,
    defaultValues: () => ({ comment: '' }),
    perform: async (targets: Target[], values: CommentValues) => {
      try {
        await config.comment(api, targets, values.comment.trim())
        return { variant: 'success', message: config.successMessage(targets.length) }
      } catch {
        return commandFailed(config.errorHeading)
      }
    }
  }
}
