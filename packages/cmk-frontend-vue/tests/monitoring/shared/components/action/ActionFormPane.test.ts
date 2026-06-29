/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import type { TranslatedString } from '@/lib/i18nString'

import ActionFormPane from '@/monitoring/shared/components/action/ActionFormPane.vue'
import type { ActionFormDefinition } from '@/monitoring/shared/components/action/types'

function mountPane(definition: ActionFormDefinition) {
  return render(ActionFormPane, {
    props: { definition, title: 'Test action' as TranslatedString }
  })
}

test('renders the comment form for a comment definition', () => {
  mountPane({ type: 'comment', ident: 'comment' })

  expect(screen.getByRole('textbox')).toBeInTheDocument()
})

test('renders no input for a confirm definition', () => {
  mountPane({ type: 'confirm', ident: 'reschedule' })

  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
})

test('keeps apply disabled until the comment is non-empty, then submits the values', async () => {
  const { emitted } = mountPane({ type: 'comment', ident: 'comment' })

  const apply = screen.getByRole('button', { name: 'Apply' })
  expect(apply).toBeDisabled()

  await userEvent.type(screen.getByRole('textbox'), 'on it')
  expect(apply).toBeEnabled()

  await userEvent.click(apply)
  expect(emitted('submit')).toEqual([[{ comment: 'on it' }]])
})

test('emits cancel from the cancel button', async () => {
  const { emitted } = mountPane({ type: 'confirm', ident: 'reschedule' })

  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(emitted('cancel')).toHaveLength(1)
})
