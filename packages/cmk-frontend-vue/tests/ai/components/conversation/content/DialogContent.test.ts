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
  return render(DialogContent, { props: { content_type: 'dialog', ...props } })
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

  test('shows the title as the heading of the alert box', () => {
    renderDialogContent({ message: 'Hello', title: 'Notice' })

    screen.getByRole('heading', { name: 'Notice' })
  })
})
