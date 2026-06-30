/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { markRaw } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import ActionFormPane from '@/monitoring/shared/components/action/ActionFormPane.vue'
import CommentForm from '@/monitoring/shared/components/action/actions/CommentForm.vue'

test('renders the given form and gates submit on its validity', async () => {
  const { emitted } = render(ActionFormPane, {
    props: {
      title: 'Add comment' as TranslatedString,
      form: markRaw(CommentForm),
      initialValues: { comment: '' }
    }
  })

  const apply = screen.getByRole('button', { name: 'Apply' })
  expect(apply).toBeDisabled()

  await userEvent.type(screen.getByRole('textbox'), 'on it')
  expect(apply).toBeEnabled()

  await userEvent.click(apply)
  expect(emitted('submit')).toEqual([[{ comment: 'on it' }]])
})

test('renders no inputs and is immediately submittable without a form', async () => {
  const { emitted } = render(ActionFormPane, {
    props: { title: 'Reschedule' as TranslatedString, initialValues: {} }
  })

  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  const apply = screen.getByRole('button', { name: 'Apply' })
  expect(apply).toBeEnabled()

  await userEvent.click(apply)
  expect(emitted('submit')).toEqual([[{}]])
})

test('honors a custom submit label and emits cancel', async () => {
  const { emitted } = render(ActionFormPane, {
    props: {
      title: 'Acknowledge problems' as TranslatedString,
      submitLabel: 'Acknowledge' as TranslatedString,
      initialValues: {}
    }
  })

  expect(screen.getByRole('button', { name: 'Acknowledge' })).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(emitted('cancel')).toHaveLength(1)
})
