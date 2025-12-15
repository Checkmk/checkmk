/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api, type ApiResponseBody } from '@/lib/api-client'
import { randomId } from '@/lib/randomId'

export interface AiBaseRequestResponse {
  user_id?: string | undefined
  request_id?: string | undefined
}

export interface EnsuredAiBaseRequestResponse extends AiBaseRequestResponse {
  request_id: string
}

export interface AiBaseLlmResponse extends AiBaseRequestResponse {
  model: string
  provider: string
}

export interface InfoResponse {
  service_name: string
  version: string
  models: string[]
  provider: string
}
export interface DataToBeProvidedToLlmResponse extends AiBaseRequestResponse {
  list_host_cols: string[]
  list_service_cols: string[]
}

export interface AiServiceAction {
  action_id: string
  action_name: string
}

export interface EnumerateActionsResponse {
  all_possible_action_types: AiServiceAction[]
}

export interface AiInferenceRequest extends AiBaseRequestResponse {
  action_type: AiServiceAction
  data: unknown
  history?: unknown[] | undefined
}

export interface AiInferenceResponse extends AiBaseLlmResponse {
  response: AiInference
}

export interface AiInferenceUsedResource {
  host_id: string
  service_id: string
  list_of_used_fields: string
}

export interface AiExplanationSection {
  title: string
  content: string
  content_type: 'markdown' | 'json'
}

export interface AiInference extends AiBaseLlmResponse {
  explanation_sections: AiExplanationSection[]
  used_resources: AiInferenceUsedResource[]
}

export class AiApiClient extends Api {
  public constructor(private user_id: string | null = null) {
    // no leading slash to use the given base url and path https://hostname.tld/sitename/check_mk/
    super('ai-service/v1/', [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json']
    ])
  }

  public async getInfo(): Promise<InfoResponse> {
    return this.get(`info?request_id=${randomId()}`) as Promise<InfoResponse>
  }

  public async getUserActions(templateId: string): Promise<AiServiceAction[]> {
    return (
      (await this.get(
        `enumerate-actions?request_id=${randomId()}&template_id=${templateId}`
      )) as EnumerateActionsResponse
    ).all_possible_action_types
  }

  public async inference(
    action: AiServiceAction,
    data: unknown,
    history?: unknown[]
  ): Promise<AiInference> {
    const options: AiInferenceRequest = {
      action_type: action,
      data,
      history
    }

    const res = (await this.post('inference', this.ensureAiRequest(options))) as AiInferenceResponse

    if (typeof res.response === 'string') {
      res.response = JSON.parse(res.response as string) as AiInference
    }

    return res.response
  }

  public override get(url: string): Promise<AiBaseRequestResponse> {
    return this.getRaw(url) as Promise<ApiResponseBody<AiBaseRequestResponse>>
  }

  public override post(url: string, data: AiBaseRequestResponse): Promise<AiBaseRequestResponse> {
    return this.postRaw(url, data) as Promise<ApiResponseBody<AiBaseRequestResponse>>
  }

  protected ensureAiRequest(data: AiBaseRequestResponse): EnsuredAiBaseRequestResponse {
    if (this.user_id) {
      data.user_id = this.user_id
    }
    data.request_id = data.request_id ?? randomId()
    return data as EnsuredAiBaseRequestResponse
  }
}
