/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import usePersistentRef from '@/lib/usePersistentRef'

import type { AiApiClient } from '@/ai/lib/ai-api-client'

export interface IAiConversationConfig<T> {
  user_id: string
  data?: T
  conversationId?: string | undefined
  dataToProvideToLlm?: () => Promise<TAiConversationElementContent[]> | undefined
}

export type TBaseConversationElementContent = { (e: 'done'): void }

export interface BaseConversationElementContent {
  type: string
  title?: string | undefined
  noAnimation?: boolean | undefined
}

export type TAiConversationElementContent = BaseConversationElementContent
export interface IAiConversationElement {
  role: AiConversationElementRole
  content:
    | TAiConversationElementContent[]
    | Promise<TAiConversationElementContent[]>
    | (() => Promise<TAiConversationElementContent[]>)
  noAnimation?: boolean | undefined
  hideControls?: boolean | undefined
  loadingText?: string | undefined
  error?: string | undefined
}

export interface IAiConversation<T> {
  config: IAiConversationConfig<T>
  elements: Ref<IAiConversationElement[]>
}

export type AiConversationElementRole = 'user' | 'ai' | 'system'

export class AiConversationBaseTemplate {
  public conversationOpen = ref(false)
  public consented: Ref<boolean>
  public elements: Ref<IAiConversationElement[]> = ref<IAiConversationElement[]>([])

  constructor(
    public config: IAiConversationConfig<unknown>,
    protected api: AiApiClient
  ) {
    this.consented = usePersistentRef<boolean>(`ai-consent-${this.config.user_id}`, false, 'local')
    if (!this.consented.value) {
      this.config.dataToProvideToLlm = this.getDataToBeProvidedToAi.bind(this)
    }

    this.elements.value = this.getInitialElements()
  }

  public persistConsent() {
    this.consented.value = false
  }

  public addElement(element: IAiConversationElement) {
    const elements = this.elements.value.slice()
    elements.push(element)

    this.elements.value = elements
  }

  public getTemplate(): IAiConversation<unknown> {
    return {
      config: this.config,
      elements: this.elements
    }
  }

  public async getDataToBeProvidedToAi(): Promise<TAiConversationElementContent[]> {
    throw new Error('This function should be overridden by implementing class')
  }

  protected getInitialElements(): IAiConversationElement[] {
    return []
  }

  protected setConfigData(_data: unknown) {
    throw new Error('This function should be overridden by implementing class')
  }
}
