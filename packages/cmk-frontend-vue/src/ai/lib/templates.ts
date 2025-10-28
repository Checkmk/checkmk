/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AiTemplateId } from 'cmk-shared-typing/typescript/ai_button'

import { AiApiClient } from './ai-api-client'
import type { AiConversationBaseTemplate } from './conversation-templates/base-template'
import { ExplainThisIssueAiTemplate } from './conversation-templates/explain-this-issue'

export const AI_CONVERSATION_TEMPLATES = {
  'explain-this-issue': ExplainThisIssueAiTemplate
}

export function getAiTemplate(
  id: AiTemplateId,
  // eslint-disable-next-line @typescript-eslint/naming-convention
  user_id: string,
  data: unknown
): AiConversationBaseTemplate {
  const template = AI_CONVERSATION_TEMPLATES[id]

  if (!template) {
    throw new Error('Template not found')
  }

  const aiTemplate = new template(
    {
      user_id
    },
    new AiApiClient()
  )

  aiTemplate.setConfigData(data as typeof aiTemplate.data)

  return aiTemplate
}
