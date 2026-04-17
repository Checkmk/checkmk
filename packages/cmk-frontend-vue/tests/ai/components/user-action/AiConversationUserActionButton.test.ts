/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'

import AiConversationUserActionButton from '@/ai/components/user-action/AiConversationUserActionButton.vue'
import type { AiActionButton } from '@/ai/lib/service/ai-template'

function renderButton(props: Partial<AiActionButton> = {}) {
  return render(AiConversationUserActionButton, {
    props: {
      action_id: 'some-action',
      action_name: 'Do Something',
      ...props
    },
    global: {
      stubs: {
        CmkButton: {
          props: ['disabled', 'variant'],
          template:
            '<button type="button" :disabled="disabled" :data-variant="variant"><slot /></button>'
        },
        CmkIcon: {
          props: ['name'],
          template: '<span data-testid="cmk-icon" :data-name="name" />'
        }
      }
    }
  })
}

describe('AiConversationUserActionButton', () => {
  test('renders the action name', () => {
    renderButton({ action_name: 'Explain this service' })

    expect(screen.getByText('Explain this service')).toBeInTheDocument()
  })

  test('shows sparkle icon when not yet executed', () => {
    renderButton({ executed: false })

    expect(screen.getByTestId('cmk-icon')).toHaveAttribute('data-name', 'sparkle')
  })

  test('shows sparkle icon when executed is undefined', () => {
    renderButton({})

    expect(screen.getByTestId('cmk-icon')).toHaveAttribute('data-name', 'sparkle')
  })

  test('shows alert-up icon when the action has been executed', () => {
    renderButton({ executed: true })

    expect(screen.getByTestId('cmk-icon')).toHaveAttribute('data-name', 'alert-up')
  })
})
