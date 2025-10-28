/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkState } from '@/lib/cmkState'
import usei18n from '@/lib/i18n'

import type { AiApiClient } from '@/ai/lib/ai-api-client'
import { AiRole } from '@/ai/lib/utils'

import {
  AiConversationBaseTemplate,
  type IAiConversationConfig,
  type IAiConversationElement,
  type TAiConversationElementContent
} from './base-template'

const { _t } = usei18n()

export interface ExplainThisIssueConfigData {
  host: string
  service: string
  state: CmkState
}

export class ExplainThisIssueAiTemplate extends AiConversationBaseTemplate {
  public data: ExplainThisIssueConfigData

  constructor(
    public override config: IAiConversationConfig<ExplainThisIssueConfigData>,
    api: AiApiClient
  ) {
    super(config, api)
    this.data = this.config.data as ExplainThisIssueConfigData
  }

  protected override getInitialElements(): IAiConversationElement[] {
    return [
      {
        role: AiRole.ai,
        content: this.getInference.bind(this),
        loadingText: _t('Analyzing data...')
      }
    ]
  }

  public override setConfigData(data: ExplainThisIssueConfigData): void {
    this.data = this.config.data = data
  }

  public override async getDataToBeProvidedToAi(): Promise<TAiConversationElementContent[]> {
    return []
  }

  protected async getInference(): Promise<TAiConversationElementContent[]> {
    return []
  }
}
