/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { RowSelectionState } from '@tanstack/vue-table'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { nextTick, ref } from 'vue'

import { useMonitoringActions } from '@/monitoring/shared/services/useMonitoringActions'

const onOffer = (...keys: string[]) => ref<readonly string[]>(keys)

test('opens and closes an action', () => {
  const actions = useMonitoringActions<'acknowledge'>(ref<RowSelectionState>({}), onOffer())

  actions.openAction('acknowledge')
  expect(actions.activeAction.value).toBe('acknowledge')

  actions.closeAction()
  expect(actions.activeAction.value).toBeNull()
})

test('feedback stores the message and closes the pane', () => {
  const actions = useMonitoringActions<'acknowledge'>(
    ref<RowSelectionState>({ 'heute/web-01': true }),
    onOffer('heute/web-01')
  )
  actions.openAction('acknowledge')

  actions.applyFeedback({ variant: 'success', message: 'done' as TranslatedString })

  expect(actions.feedback.value).toEqual({ variant: 'success', message: 'done' })
  expect(actions.feedbackOpen.value).toBe(true)
  expect(actions.activeAction.value).toBeNull()
})

test('feedback of a command run outside the pane leaves the pane open', () => {
  const actions = useMonitoringActions<'acknowledge'>(ref<RowSelectionState>({}), onOffer())
  actions.openAction('acknowledge')

  actions.showFeedback({ variant: 'success', message: 'done' as TranslatedString })

  expect(actions.feedbackOpen.value).toBe(true)
  expect(actions.activeAction.value).toBe('acknowledge')
})

test('feedback keeps the selection, as the legacy views do', () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true })
  const actions = useMonitoringActions<'acknowledge'>(rowSelection, onOffer('heute/web-01'))

  actions.applyFeedback({ variant: 'success', message: 'done' as TranslatedString })

  expect(rowSelection.value).toEqual({ 'heute/web-01': true })
})

test('closes the open pane once the selection empties', async () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true })
  const actions = useMonitoringActions<'acknowledge'>(rowSelection, onOffer('heute/web-01'))
  actions.openAction('acknowledge')

  rowSelection.value = {}
  await nextTick()

  expect(actions.activeAction.value).toBeNull()
})

test('a selected row that leaves the offer is dropped from the selection', async () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true, 'heute/db-01': true })
  const keys = onOffer('heute/web-01', 'heute/db-01')
  const actions = useMonitoringActions<'acknowledge'>(rowSelection, keys)

  keys.value = ['heute/web-01']
  await nextTick()

  expect(rowSelection.value).toEqual({ 'heute/web-01': true })
  expect(actions.selectedCount.value).toBe(1)
})

test('a selection survives rows arriving and reordering around it', async () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true })
  const keys = onOffer('heute/web-01', 'heute/db-01')
  useMonitoringActions<'acknowledge'>(rowSelection, keys)

  keys.value = ['heute/db-01', 'heute/web-01', 'heute/app-01']
  await nextTick()

  expect(rowSelection.value).toEqual({ 'heute/web-01': true })
})

test('the open pane closes once the last selected row leaves the offer', async () => {
  const rowSelection = ref<RowSelectionState>({ 'heute/web-01': true })
  const keys = onOffer('heute/web-01')
  const actions = useMonitoringActions<'acknowledge'>(rowSelection, keys)
  actions.openAction('acknowledge')

  keys.value = ['heute/db-01']
  await nextTick()

  expect(actions.activeAction.value).toBeNull()
})
