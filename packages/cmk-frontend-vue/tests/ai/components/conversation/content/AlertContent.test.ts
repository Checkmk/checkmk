/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import AlertContent from '@/ai/components/conversation/content/AlertContent.vue'
import type { AlertConversationElementContent } from '@/ai/lib/service/ai-template'

type AlertVariant = AlertConversationElementContent['variant']

function renderAlertContent(
  props: { variant: AlertVariant; text: string; title?: string } = {
    variant: 'error',
    text: 'Something went wrong'
  }
) {
  return render(AlertContent, {
    props: { content_type: 'alert', ...props },
    global: {
      stubs: {
        CmkAlertBox: {
          props: ['variant'],
          template: '<div data-testid="alert-box" :data-variant="variant"><slot /></div>'
        }
      }
    }
  })
}

describe('AlertContent', () => {
  test('emits done immediately on mount', () => {
    const { emitted } = renderAlertContent()

    expect(emitted('done')).toHaveLength(1)
  })

  test('passes the variant to the alert box', () => {
    renderAlertContent({ variant: 'warning', text: 'Watch out' })

    expect(screen.getByTestId('alert-box')).toHaveAttribute('data-variant', 'warning')
  })

  test('renders the alert text', () => {
    renderAlertContent({ variant: 'error', text: 'Critical failure' })

    expect(screen.getByText('Critical failure')).toBeInTheDocument()
  })
})
