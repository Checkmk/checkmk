/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AiActionButton, AiTemplateService } from '@/ai/lib/service/ai-template'

interface LoadUserActionsOptions {
  autoExecuteSingleAction?: boolean
}

export async function loadUserActions(
  aiTemplate: AiTemplateService | null,
  options: LoadUserActionsOptions = {}
): Promise<AiActionButton[] | Error> {
  const { autoExecuteSingleAction = true } = options
  const actions = await aiTemplate?.getUserActionButtons()
  if (actions instanceof Error) {
    return actions
  }

  const userActions = actions ?? []

  // Auto trigger service action if it is the only action.
  if (
    autoExecuteSingleAction &&
    userActions.length === 1 &&
    userActions[0]?.action_id === 'explain_this_service'
  ) {
    void aiTemplate?.execUserActionButton(userActions[0])
  }

  return userActions
}
