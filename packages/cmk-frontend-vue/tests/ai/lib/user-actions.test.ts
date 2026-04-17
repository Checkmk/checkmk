/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { AiActionButton } from '@/ai/lib/service/ai-template'
import { loadUserActions } from '@/ai/lib/user-actions'

function makeAction(overrides: Partial<AiActionButton> = {}): AiActionButton {
  return { action_id: 'explain', action_name: 'Explain', ...overrides }
}

function makeTemplate(actions: AiActionButton[] | Error) {
  return {
    getUserActionButtons: vi.fn().mockResolvedValue(actions),
    execUserActionButton: vi.fn()
  }
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('loadUserActions', () => {
  test('returns the error when getUserActionButtons resolves to an Error', async () => {
    const error = new Error('network failure')
    const template = makeTemplate(error)

    const result = await loadUserActions(template as never)

    expect(result).toBe(error)
  })

  test('returns an empty array when there are no actions', async () => {
    const template = makeTemplate([])

    const result = await loadUserActions(template as never)

    expect(result).toEqual([])
  })

  test('returns all actions when multiple actions are present', async () => {
    const actions = [makeAction({ action_id: 'a' }), makeAction({ action_id: 'b' })]
    const template = makeTemplate(actions)

    const result = await loadUserActions(template as never)

    expect(result).toEqual(actions)
  })

  test('auto-executes the action when there is exactly one explain_this_service action', async () => {
    const action = makeAction({ action_id: 'explain_this_service' })
    const template = makeTemplate([action])

    await loadUserActions(template as never)

    expect(template.execUserActionButton).toHaveBeenCalledOnce()
    expect(template.execUserActionButton).toHaveBeenCalledWith(action)
  })

  test('does NOT auto-execute when there are multiple actions', async () => {
    const actions = [
      makeAction({ action_id: 'explain_this_service' }),
      makeAction({ action_id: 'other' })
    ]
    const template = makeTemplate(actions)

    await loadUserActions(template as never)

    expect(template.execUserActionButton).not.toHaveBeenCalled()
  })

  test('does NOT auto-execute when the single action has a different id', async () => {
    const action = makeAction({ action_id: 'something_else' })
    const template = makeTemplate([action])

    await loadUserActions(template as never)

    expect(template.execUserActionButton).not.toHaveBeenCalled()
  })

  test('does NOT auto-execute when autoExecuteSingleAction is false', async () => {
    const action = makeAction({ action_id: 'explain_this_service' })
    const template = makeTemplate([action])

    await loadUserActions(template as never, { autoExecuteSingleAction: false })

    expect(template.execUserActionButton).not.toHaveBeenCalled()
  })

  test('returns empty array and does not throw when template is null', async () => {
    const result = await loadUserActions(null)

    expect(result).toEqual([])
  })
})
