/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { ref } from 'vue'

import AiConversationUserAction from '@/ai/components/user-action/AiConversationUserAction.vue'
import { aiTemplateKey } from '@/ai/lib/provider/ai-template'
import type { AiActionButton } from '@/ai/lib/service/ai-template'
import { loadUserActions } from '@/ai/lib/user-actions'

vi.mock('@/ai/lib/user-actions')

const mockLoadUserActions = vi.mocked(loadUserActions)

function makeAction(overrides: Partial<AiActionButton> = {}): AiActionButton {
  return { action_id: 'explain', action_name: 'Explain', ...overrides }
}

function renderComponent(execUserActionButton = vi.fn()) {
  const mockTemplate = { execUserActionButton }
  render(AiConversationUserAction, {
    global: {
      provide: {
        [aiTemplateKey as symbol]: ref(mockTemplate)
      },
      stubs: {
        CmkHeading: {
          template: '<div data-testid="heading"><slot /></div>'
        },
        CmkSkeleton: {
          template: '<div data-testid="skeleton" />'
        },
        AiConversationUserActionButton: {
          props: ['action_id', 'action_name', 'executed'],
          // v-bind="$attrs" forwards onClick from the parent @click listener
          template:
            '<button type="button" v-bind="$attrs" :data-action-id="action_id">{{ action_name }}</button>'
        },
        AlertContent: {
          props: ['variant', 'text', 'title'],
          template:
            '<div data-testid="alert-content" :data-variant="variant" :data-title="title">{{ text }}</div>'
        }
      }
    }
  })
  return { mockTemplate }
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('AiConversationUserAction — loading state', () => {
  test('shows 3 skeletons before actions have loaded', () => {
    mockLoadUserActions.mockReturnValue(new Promise(() => {}))

    renderComponent()

    expect(screen.getAllByTestId('skeleton')).toHaveLength(3)
  })

  test('hides skeletons once actions have loaded', async () => {
    mockLoadUserActions.mockResolvedValue([makeAction()])

    renderComponent()

    await waitFor(() => {
      expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument()
    })
  })
})

describe('AiConversationUserAction — rendering actions', () => {
  test('renders a button for each non-executed action', async () => {
    const actions = [
      makeAction({ action_id: 'a', action_name: 'Action A' }),
      makeAction({ action_id: 'b', action_name: 'Action B' })
    ]
    mockLoadUserActions.mockResolvedValue(actions)

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Action A')).toBeInTheDocument()
      expect(screen.getByText('Action B')).toBeInTheDocument()
    })
  })

  test('does not render executed actions', async () => {
    mockLoadUserActions.mockResolvedValue([
      makeAction({ action_id: 'done', action_name: 'Already Done', executed: true }),
      makeAction({ action_id: 'pending', action_name: 'Pending Action', executed: false })
    ])

    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Pending Action')).toBeInTheDocument()
    })
    expect(screen.queryByText('Already Done')).not.toBeInTheDocument()
  })

  test('shows the heading when there are non-executed actions', async () => {
    mockLoadUserActions.mockResolvedValue([makeAction()])

    renderComponent()

    await waitFor(() => {
      expect(screen.getByTestId('heading')).toBeInTheDocument()
      expect(screen.getByText('What would you like the AI to do?')).toBeInTheDocument()
    })
  })

  test('hides the heading when all actions are executed', async () => {
    mockLoadUserActions.mockResolvedValue([makeAction({ executed: true })])

    renderComponent()

    await waitFor(() => {
      // wait for load to settle
      expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument()
    })
    expect(screen.queryByTestId('heading')).not.toBeInTheDocument()
  })
})

describe('AiConversationUserAction — click behavior', () => {
  test('clicking an action button calls execUserActionButton with the correct action', async () => {
    const execUserActionButton = vi.fn()
    const action = makeAction({ action_id: 'explain', action_name: 'Explain' })
    mockLoadUserActions.mockResolvedValue([action])

    renderComponent(execUserActionButton)

    await waitFor(() => {
      expect(screen.getByText('Explain')).toBeInTheDocument()
    })

    await fireEvent.click(screen.getByText('Explain'))

    expect(execUserActionButton).toHaveBeenCalledOnce()
    expect(execUserActionButton).toHaveBeenCalledWith(action)
  })
})

describe('AiConversationUserAction — empty and error states', () => {
  test('shows "No actions found" warning when the actions list is empty', async () => {
    mockLoadUserActions.mockResolvedValue([])

    renderComponent()

    await waitFor(() => {
      expect(screen.getByTestId('alert-content')).toHaveAttribute('data-variant', 'warning')
      expect(screen.getByText('No actions found')).toBeInTheDocument()
    })
  })

  test('shows an error alert when loading actions fails', async () => {
    mockLoadUserActions.mockResolvedValue(new Error('network failure'))

    renderComponent()

    await waitFor(() => {
      expect(screen.getByTestId('alert-content')).toHaveAttribute('data-variant', 'error')
      expect(
        screen.getByText('Error retrieving available AI actions. Please try again later.')
      ).toBeInTheDocument()
    })
  })
})
