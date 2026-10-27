/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import {
  CustomNotificationApi,
  type CustomNotificationOptions
} from '@/monitoring/shared/api/actions/customNotification'

import type { ActionTargetKind, MonitoringAction } from '../types'
import CustomNotificationForm, { type CustomNotificationValues } from './CustomNotificationForm.vue'
import { commandFailed } from './feedback'

export const CUSTOM_NOTIFICATION_ACTION_ID = 'send_custom_notification'

export interface CustomNotificationKindConfig<Target> {
  targetKind: ActionTargetKind
  notify(
    api: CustomNotificationApi,
    targets: Target[],
    options: CustomNotificationOptions
  ): Promise<number>
  successMessage(count: number): TranslatedString
  errorHeading: TranslatedString
}

/** Shared custom notification flow for hosts and services: only the API call and wording differ. */
export function createCustomNotificationAction<Target>(
  config: CustomNotificationKindConfig<Target>
): MonitoringAction<CustomNotificationValues, Target> {
  const { _t } = usei18n()
  const api = new CustomNotificationApi()

  return {
    id: CUSTOM_NOTIFICATION_ACTION_ID,
    title: _t('Send custom notification'),
    submitLabel: _t('Send'),
    description: [
      _t('Manually trigger notifications to verify your notification setup is working.')
    ],
    form: CustomNotificationForm,
    formProps: { targetKind: config.targetKind },
    defaultValues: () => ({ comment: '', forced: false, broadcast: false }),
    perform: async (targets: Target[], values: CustomNotificationValues) => {
      try {
        const count = await config.notify(api, targets, {
          ...values,
          comment: values.comment.trim()
        })
        return { variant: 'success', message: config.successMessage(count) }
      } catch {
        return commandFailed(config.errorHeading)
      }
    }
  }
}
