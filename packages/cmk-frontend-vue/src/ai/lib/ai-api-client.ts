/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Api, type ApiResponseBody } from '@/lib/api-client'
import { randomId } from '@/lib/randomId'

import { streamJsonResponse } from './utils'

export type AiBaseRequestResponse = object

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
  context_data: unknown
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

export interface MetadataEvent {
  type: 'metadata'
  model?: string
}

export interface ThinkingEvent {
  type: 'thinking'
  text: string
}

export interface AnswerEvent {
  type: 'answer'
  text: string
}

export interface ErrorEvent {
  type: 'error'
  message: string
}

export interface FinishEvent {
  type: 'finish'
}

export type StreamEvent = MetadataEvent | ThinkingEvent | AnswerEvent | ErrorEvent | FinishEvent

// Must exceed the ai_service keepalive ping interval (currently 15s).
const STREAM_TIMEOUT_MS = 20_000

export class AiApiClient extends Api {
  private readonly defaultHeaders: Record<string, string>
  public constructor(siteName: string) {
    // no leading slash to use the given base url and path https://hostname.tld/sitename/check_mk/
    const headers: [string, string][] = [
      ['Content-Type', 'application/json'],
      ['Accept', 'application/json'],
      ['x-checkmk-site-name', siteName]
      // Uncomment the next two lines for local testing,
      // in production the reverse proxy will set the correct host header:
      // ,['x-forwarded-host', 'localhost:3000'],
      // ['x-forwarded-proto', 'http']
    ]

    super('ai-service/api/v1/', headers)
    this.defaultHeaders = Object.fromEntries(headers)
  }

  public async getInfo(): Promise<InfoResponse> {
    return this.get('info') as Promise<InfoResponse>
  }

  public async getUserActions(templateId: string): Promise<AiServiceAction[]> {
    return (
      (await this.get(
        `enumerate-action-types?template_id=${templateId}`
      )) as EnumerateActionsResponse
    ).all_possible_action_types
  }

  public async streamInference(
    action: AiServiceAction,
    contextData: unknown,
    onEvent: (event: StreamEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void,
    signal?: AbortSignal
  ): Promise<void> {
    const options: AiInferenceRequest = {
      action_type: action,
      context_data: contextData
    }

    try {
      const res = await fetch(`${this.baseUrl}stream-inference`, {
        method: 'POST',
        headers: {
          ...this.defaultHeaders,
          'x-saas-request-id': randomId()
        },
        body: JSON.stringify(options),
        signal: signal ?? null
      })

      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`Stream inference request failed: ${errorText}`)
      }

      if (!res.body) {
        throw new Error('Stream inference response body is null')
      }

      const jsonStream = streamJsonResponse(res.body, STREAM_TIMEOUT_MS)

      let lastEvent: StreamEvent | undefined
      for await (const chunk of jsonStream) {
        lastEvent = chunk as StreamEvent
        if (lastEvent.type === 'error') {
          throw new Error(`Error event received: ${lastEvent.message}`)
        }
        onEvent(lastEvent)
      }

      if (lastEvent?.type === 'finish') {
        onComplete?.()
      } else {
        throw new Error('Stream did not complete successfully')
      }
    } catch (e) {
      onError?.(e instanceof Error ? e : new Error(String(e)))
    }
  }

  public async inference(
    action: AiServiceAction,
    contextData: unknown,
    history?: unknown[]
  ): Promise<AiInference> {
    const options: AiInferenceRequest = {
      action_type: action,
      context_data: contextData,
      history
    }

    const res = (await this.post('inference', options)) as AiInferenceResponse

    if (typeof res.response === 'string') {
      res.response = JSON.parse(res.response as string) as AiInference
    }

    return res.response
  }

  public override get(url: string): Promise<AiBaseRequestResponse> {
    return this.getRaw(url, {
      headers: [['x-saas-request-id', randomId()]]
    }) as Promise<ApiResponseBody<AiBaseRequestResponse>>
  }

  public override post(url: string, data: AiBaseRequestResponse): Promise<AiBaseRequestResponse> {
    return this.postRaw(url, data, {
      headers: [['x-saas-request-id', randomId()]]
    }) as Promise<ApiResponseBody<AiBaseRequestResponse>>
  }
}
