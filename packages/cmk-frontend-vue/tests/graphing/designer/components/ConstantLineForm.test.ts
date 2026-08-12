/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import ConstantLineForm from '@/graphing/designer/components/forms/ConstantLineForm.vue'
import { type GraphItemsStore, useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { type DraftConstantItem, newConstantDraft } from '@/graphing/designer/drafts'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

function renderForm(draft: DraftConstantItem): GraphItemsStore {
  const store = useGraphItems(PALETTE)
  store.replaceAll([draft])
  render(ConstantLineForm, { props: { item: draft, store } })
  return store
}

test('entering a value completes a constant', async () => {
  const store = renderForm(newConstantDraft('A', '#28a2f3'))

  await fireEvent.update(screen.getByRole('spinbutton', { name: 'Constant at' }), '42')

  expect(store.items.value[0]).toMatchObject({ type: 'constant', value: 42 })
})

test('clearing the value leaves the constant unset rather than blank', async () => {
  const store = renderForm({ ...newConstantDraft('A', '#28a2f3'), value: 42 })

  await fireEvent.update(screen.getByRole('spinbutton', { name: 'Constant at' }), '')

  expect(store.items.value[0]).toMatchObject({ type: 'constant', value: null })
})
