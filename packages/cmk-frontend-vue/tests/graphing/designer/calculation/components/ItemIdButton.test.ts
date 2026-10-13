/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'

import ItemIdButton from '@/graphing/designer/calculation/components/ItemIdButton.vue'

function renderButton(props: Record<string, unknown> = {}) {
  return render(ItemIdButton, {
    props: { id: 'A', label: untranslated('Insert A'), ...props }
  })
}

test('emits click and takes its accessible name from the label', async () => {
  const { emitted } = renderButton()
  await fireEvent.click(screen.getByRole('button', { name: 'Insert A' }))
  expect(emitted('click')).toHaveLength(1)
})

test('a block reason disables the button and explains it on hover', () => {
  renderButton({ blockReason: untranslated('Aggregate this query first') })
  const button = screen.getByRole('button', { name: 'Insert A' })
  expect(button).toHaveAttribute('aria-disabled', 'true')
  expect(button).toHaveAttribute('title', 'Aggregate this query first')
})

test('stays actionable without a block reason', async () => {
  const { emitted } = renderButton({ blockReason: null })
  await fireEvent.click(screen.getByRole('button', { name: 'Insert A' }))
  expect(emitted('click')).toHaveLength(1)
})
