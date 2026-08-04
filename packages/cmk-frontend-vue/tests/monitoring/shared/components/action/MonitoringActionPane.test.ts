/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { markRaw, ref } from 'vue'

import type { HostRef } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { ActionFeedback } from '@/monitoring/shared/components/action/ActionFeedback.vue'
import MonitoringActionPane from '@/monitoring/shared/components/action/MonitoringActionPane.vue'
import AcknowledgeForm from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

const TWO_HOSTS: HostRef[] = [
  { site_id: 'heute', name: 'web-01' },
  { site_id: 'heute', name: 'web-02' }
]

const ackAction: MonitoringAction = {
  id: 'acknowledge',
  title: 'Acknowledge problems' as TranslatedString,
  submitLabel: 'Acknowledge' as TranslatedString,
  form: markRaw(AcknowledgeForm),
  defaultValues: () => ({
    comment: '',
    expireOnEnabled: false,
    expireOn: null,
    sticky: false,
    persistent: false,
    notify: true
  }),
  perform: async (targets) =>
    ({ variant: 'success', message: `Acknowledged ${targets.length}` }) as ActionFeedback
}

const REGISTRY = { acknowledge: ackAction }

function mountPane(actionId: string, targets: HostRef[] = TWO_HOSTS, total = 12) {
  const service = { total: ref(total) } as unknown as MonitoringService<unknown>
  return render(MonitoringActionPane, {
    props: { actionId, actions: REGISTRY, targets },
    global: { provide: { [MONITORING_SERVICE as symbol]: service } }
  })
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

test('resolves the action by id, gates submit on a comment, and bubbles feedback', async () => {
  const { emitted } = mountPane('acknowledge')

  const apply = screen.getByRole('button', { name: 'Acknowledge' })
  expect(apply).toBeDisabled()

  await userEvent.type(screen.getByPlaceholderText('Enter a comment…'), 'disk full')
  expect(apply).toBeEnabled()

  await userEvent.click(apply)
  await flush()

  const events = emitted('feedback') as ActionFeedback[][]
  expect(events).toHaveLength(1)
  expect(events[0]?.[0]).toEqual({ variant: 'success', message: 'Acknowledged 2' })
})

test('emits cancel without feedback', async () => {
  const { emitted } = mountPane('acknowledge')

  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(emitted('cancel')).toHaveLength(1)
  expect(emitted('feedback')).toBeUndefined()
})

test('relates the selection to the loaded rows, in singular and plural', () => {
  const { unmount } = mountPane('acknowledge')
  expect(screen.getByText('Selected hosts: 2 | Total hosts: 12')).toBeInTheDocument()
  unmount()

  mountPane('acknowledge', TWO_HOSTS.slice(0, 1))
  expect(screen.getByText('Selected host: 1 | Total hosts: 12')).toBeInTheDocument()
})

test('renders nothing for an unknown action id', () => {
  mountPane('does-not-exist')

  expect(screen.queryByRole('button', { name: 'Acknowledge' })).not.toBeInTheDocument()
})
