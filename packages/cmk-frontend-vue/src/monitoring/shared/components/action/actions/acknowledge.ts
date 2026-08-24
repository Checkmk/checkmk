/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import {
  AcknowledgeApi,
  type AcknowledgeOptions
} from '@/monitoring/shared/api/actions/acknowledge'

import type { ActionTargetKind, MonitoringAction } from '../types'
import AcknowledgeForm, { type AcknowledgeValues } from './AcknowledgeForm.vue'

export const ACK_ACTION_ID = 'acknowledge'

/** The setup pages the form links to; the server omits what the user may not edit. */
export interface AcknowledgeLinks {
  presetsUrl: string | null
  notificationRulesUrl: string | null
}

export interface AcknowledgeKindConfig<Target> {
  targetKind: ActionTargetKind
  links: AcknowledgeLinks
  /** Perform the API call for the selected targets and return the count actually acted on. */
  acknowledge(api: AcknowledgeApi, targets: Target[], options: AcknowledgeOptions): Promise<number>
  successMessage(count: number): TranslatedString
}

/** Shared acknowledgement flow for hosts and services: only the API call and wording differ. */
export function createAcknowledgeAction<Target>(
  config: AcknowledgeKindConfig<Target>
): MonitoringAction<AcknowledgeValues, Target> {
  const { _t } = usei18n()
  const api = new AcknowledgeApi()

  return {
    id: ACK_ACTION_ID,
    title: _t('Acknowledge problems'),
    submitLabel: _t('Acknowledge'),
    form: AcknowledgeForm,
    formProps: {
      targetKind: config.targetKind,
      presetsUrl: config.links.presetsUrl,
      notificationRulesUrl: config.links.notificationRulesUrl
    },
    defaultValues: () => ({
      comment: '',
      expireOnEnabled: false,
      expireOn: null,
      sticky: false,
      persistent: false,
      notify: true
    }),
    perform: async (targets: Target[], values: AcknowledgeValues) => {
      try {
        const count = await config.acknowledge(api, targets, {
          comment: values.comment,
          sticky: values.sticky,
          persistent: values.persistent,
          notify: values.notify,
          expireOn: values.expireOnEnabled ? values.expireOn?.toDate().toISOString() : undefined
        })
        return { variant: 'success', message: config.successMessage(count) }
      } catch (error) {
        return {
          variant: 'error',
          message: _t('Could not acknowledge the problems: %{detail}', {
            detail: error instanceof Error ? error.message : String(error)
          })
        }
      }
    }
  }
}
