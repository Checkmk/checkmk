/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import DialogContent from '@/ai/components/conversation/content/DialogContent.vue'

function renderDialogContent(
  props: { message: string; title?: string } = { message: 'Are you sure?' }
) {
  return render(DialogContent, {
    props: { content_type: 'dialog', ...props },
    global: {
      stubs: {
        CmkDialog: {
          props: ['title', 'message'],
          template: '<div data-testid="dialog-box" :data-heading="title">{{ message }}</div>'
        }
      }
    }
  })
}

describe('DialogContent', () => {
  test('emits done immediately on mount', () => {
    const { emitted } = renderDialogContent()

    expect(emitted('done')).toHaveLength(1)
  })

  test('renders the message text', () => {
    renderDialogContent({ message: 'Confirm your action' })

    expect(screen.getByText('Confirm your action')).toBeInTheDocument()
  })

  test('passes the title as the heading to the alert box', () => {
    renderDialogContent({ message: 'Hello', title: 'Notice' })

    expect(screen.getByTestId('dialog-box')).toHaveAttribute('data-heading', 'Notice')
  })
})
