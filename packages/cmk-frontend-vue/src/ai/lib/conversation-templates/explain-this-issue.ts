/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkState } from '@/lib/cmkState'
import usei18n from '@/lib/i18n'

import type {
  AiApiClient,
  AiInference,
  DataToBeProvidedToLlmResponse
} from '@/ai/lib/ai-api-client'
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
    let res: DataToBeProvidedToLlmResponse
    try {
      res = await this.api.getDataToBeProvidedToLlm()
    } catch (e) {
      console.error('Error fetching data to be provided to LLM:', e)
      res = {
        list_host_cols: ['host_name', 'ip_address', 'os_type', 'location'],
        list_service_cols: ['service_description', 'status', 'last_check', 'performance_data']
      }
    }

    return [
      {
        type: 'dialog',
        message: _t(
          'For a comprehensive analysis, the following data will be shared with our AI model. ' +
            'This information is required for the AI to process and complete the analytical task. ' +
            'By proceeding, you acknowledge and consent to this data being shared with our AI model.'
        )
      },
      {
        type: 'code',
        title: _t('Shared data:'),
        code:
          `Host "${this.data.host}":\n` +
          ` - ${res.list_host_cols.join('\n - ')}` +
          '\n\n' +
          `Service "${this.data.service}":\n` +
          ` - ${res.list_service_cols.join('\n - ')}`
      }
    ]
  }

  protected async getInference(): Promise<TAiConversationElementContent[]> {
    let res: AiInference
    try {
      res = await this.api.inference(this.data.host, this.data.service, this.data.state)
    } catch (e) {
      console.error('Error fetching inference from AI API:', e)
      return [
        {
          type: 'alert',
          variant: 'error',
          text: "Something went wrong. We couldn't generate the explanation."
        }
      ]
    }

    const explainContent: TAiConversationElementContent[] = [
      {
        type: 'markdown',
        title: _t('Short summary'),
        markdown: res.response.short_summary
      },
      {
        type: 'markdown',
        title: _t('Detected problem'),
        markdown: res.response.detected_problem
      },
      {
        type: 'code',
        title: _t('Context'),
        code: JSON.stringify(res.response.context, null, 2)
      },
      {
        type: 'markdown',
        title: _t('Potential solutions'),
        markdown: res.response.potential_solutions
      }
    ]

    if (res.response.might_be_misconfigured) {
      explainContent.push({
        type: 'alert',
        variant: 'warning',
        text: res.response.might_be_misconfigured
      })
    }

    return explainContent
  }
}
