/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { RowSelectionState } from '@tanstack/vue-table'
import { nextTick, ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import { useMonitoringActions } from '@/monitoring/shared/services/useMonitoringActions'

test('opens and closes an action', () => {
  const actions = useMonitoringActions<'acknowledge'>(ref<RowSelectionState>({}))

  actions.openAction('acknowledge')
  expect(actions.activeAction.value).toBe('acknowledge')

  actions.closeAction()
  expect(actions.activeAction.value).toBeNull()
})

test('successful feedback clears the selection, stores the message and closes the pane', () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true })
  const actions = useMonitoringActions<'acknowledge'>(rowSelection)
  actions.openAction('acknowledge')

  actions.applyFeedback({ variant: 'success', message: 'done' as TranslatedString })

  expect(rowSelection.value).toEqual({})
  expect(actions.feedback.value).toEqual({ variant: 'success', message: 'done' })
  expect(actions.feedbackOpen.value).toBe(true)
  expect(actions.activeAction.value).toBeNull()
})

test('error feedback keeps the selection', () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true })
  const actions = useMonitoringActions<'acknowledge'>(rowSelection)

  actions.applyFeedback({ variant: 'error', message: 'nope' as TranslatedString })

  expect(rowSelection.value).toEqual({ 'heute/web-01': true })
})

test('closes the open pane once the selection empties', async () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true })
  const actions = useMonitoringActions<'acknowledge'>(rowSelection)
  actions.openAction('acknowledge')

  rowSelection.value = {}
  await nextTick()

  expect(actions.activeAction.value).toBeNull()
})
