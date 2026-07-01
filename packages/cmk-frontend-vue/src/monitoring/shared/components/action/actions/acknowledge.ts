/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

import { AcknowledgeApi } from '@/monitoring/shared/api/actions/acknowledge'
import type { HostRef } from '@/monitoring/shared/api/types'

import type { MonitoringAction } from '../types'
import AcknowledgeForm, { type AcknowledgeValues } from './AcknowledgeForm.vue'

export const ACK_ACTION_ID = 'acknowledge'

export function useAcknowledgeAction(): MonitoringAction<AcknowledgeValues> {
  const { _t, _tn } = usei18n()
  const api = new AcknowledgeApi()

  return {
    id: ACK_ACTION_ID,
    title: _t('Acknowledge problems'),
    submitLabel: _t('Acknowledge'),
    subtitle: (count) => _tn('%{count} selected host', '%{count} selected hosts', count, { count }),
    form: AcknowledgeForm,
    defaultValues: () => ({
      comment: '',
      expireOn: null,
      sticky: false,
      persistent: false,
      notify: true
    }),
    perform: async (targets: HostRef[], values: AcknowledgeValues) => {
      try {
        await api.acknowledgeHosts(
          targets.map((target) => target.name),
          {
            comment: values.comment,
            sticky: values.sticky,
            persistent: values.persistent,
            notify: values.notify,
            expireOn: values.expireOn?.toDate().toISOString()
          }
        )
        return {
          variant: 'success',
          message: _tn(
            'Acknowledged the problem for %{count} host',
            'Acknowledged the problems for %{count} hosts',
            targets.length,
            { count: targets.length }
          )
        }
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
