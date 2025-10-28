/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api, type ApiResponseBody } from '@/lib/api-client'
import { type CmkState, type CmkStateName, mapCmkState } from '@/lib/cmkState'
import { randomId } from '@/lib/randomId'

export interface ExplainThisIssue {
  short_summary: string
  detected_problem: string
  potential_solutions: string
  context: { [key: string]: unknown }
  might_be_misconfigured?: string | undefined | null
}

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

export interface DataToBeProvidedToLlmResponse extends AiBaseRequestResponse {
  list_host_cols: string[]
  list_service_cols: string[]
}

export interface AiInferenceRequest extends AiBaseRequestResponse {
  host_name: string
  service_name: string
  status: CmkStateName
}

export interface AiInferenceResponse extends AiBaseLlmResponse {
  response: ExplainThisIssue | string
}

export interface AiInference extends AiBaseLlmResponse {
  response: ExplainThisIssue
}

export class AiApiClient extends Api {
  public constructor(private user_id: string | null = null) {
    super('/ai-service/', [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json']
    ])
  }

  public async getDataToBeProvidedToLlm(): Promise<DataToBeProvidedToLlmResponse> {
    return this.get(
      `data-availability?request_id=${randomId()}`
    ) as Promise<DataToBeProvidedToLlmResponse>
  }

  public async inference(host: string, service: string, state: CmkState): Promise<AiInference> {
    const options: AiInferenceRequest = {
      host_name: host,
      service_name: service,
      status: mapCmkState(state)
    }

    const res = (await this.post('inference', this.ensureAiRequest(options))) as AiInferenceResponse

    if (typeof res.response === 'string') {
      res.response = JSON.parse(res.response as string) as ExplainThisIssue
    }

    return res as AiInference
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
