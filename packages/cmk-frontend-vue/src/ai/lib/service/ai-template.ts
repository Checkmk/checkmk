/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AiTemplateId } from 'cmk-shared-typing/typescript/ai_button'
import { type Ref, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { KeyShortcutService } from '@/lib/keyShortcuts'
import { ServiceBase } from '@/lib/service/base'
import usePersistentRef from '@/lib/usePersistentRef'

import { type ButtonProps } from '@/components/CmkButton.vue'

import { AiApiClient, type AiServiceAction } from '@/ai/lib/ai-api-client'
import { AiRole } from '@/ai/lib/utils'

const { _t } = usei18n()
export interface AiActionButton extends ButtonProps, AiServiceAction {
  executed?: boolean | undefined
}
export interface IAiUserActionConfig {
  allowChat?: boolean | undefined
  actionButtons?: AiActionButton[] | undefined | Error
  hideExecutedActions?: boolean | undefined
}

export interface IAiConversationConfig<T> {
  user_id: string
  data?: T
  conversationId?: string | undefined
  dataToProvideToLlm?: () => Promise<TAiConversationElementContent[]> | undefined
  userActions: IAiUserActionConfig
}

export type TBaseConversationElementEmits = { (e: 'done'): void }

export interface BaseConversationElementContent {
  content_type: string
  title?: string | undefined
  noAnimation?: boolean | undefined
}

export interface AlertConversationElementContent extends BaseConversationElementContent {
  content_type: 'alert'
  text: string
  variant: 'error' | 'warning' | 'success' | 'info'
}

export interface CodeBlockConversationElementContent extends BaseConversationElementContent {
  content_type: 'code'
  code: string
}

export interface DialogConversationElementContent extends BaseConversationElementContent {
  content_type: 'dialog'
  message: string
}

export interface ImageConversationElementContent extends BaseConversationElementContent {
  content_type: 'image'
  src: string
  altText?: string | undefined
}

export interface ListConversationElementContent extends BaseConversationElementContent {
  content_type: 'list'
  listType: 'ordered' | 'unordered'
  items: string[]
}

export interface MarkdownConversationElementContent extends BaseConversationElementContent {
  content_type: 'markdown'
  content: string
}

export interface TextConversationElementContent extends BaseConversationElementContent {
  content_type: 'text'
  text: string
}

export type TAiConversationElementContent =
  | AlertConversationElementContent
  | CodeBlockConversationElementContent
  | DialogConversationElementContent
  | ImageConversationElementContent
  | ListConversationElementContent
  | MarkdownConversationElementContent
  | TextConversationElementContent

export interface IAiConversationElement {
  role: AiRole
  content:
    | TAiConversationElementContent[]
    | Promise<TAiConversationElementContent[]>
    | (() => Promise<TAiConversationElementContent[]>)
  noAnimation?: boolean | undefined
  hideControls?: boolean | undefined
  loadingText?: string | undefined
  error?: string | undefined
}

export type OnAnimationActiveChangeCallback = (active: boolean) => void

export class AiTemplateService extends ServiceBase {
  public conversationOpen = ref(false)
  public elements: IAiConversationElement[] = []
  public config: IAiConversationConfig<unknown>
  public activeRole: AiRole = AiRole.user
  protected api: AiApiClient

  constructor(
    public templateId: AiTemplateId,
    public userId: string,
    public data: unknown
  ) {
    super(templateId, new KeyShortcutService(window))

    this.api = new AiApiClient(this.userId)
    this.config = {
      user_id: this.userId,
      data: this.data,
      userActions: {}
    }

    if (!this.getPersistentRef().value) {
      this.config.dataToProvideToLlm = this.getDataToBeProvidedToAi.bind(this)
    }
  }

  public isConsented(): boolean {
    return this.getPersistentRef().value
  }

  public persistConsent() {
    const consented = this.getPersistentRef()
    consented.value = true

    void this.loadAiUserActions()
  }

  public setAnimationActiveChange(active: boolean) {
    this.dispatchCallback('animation-active-change', active)
  }

  public onAnimationActiveChange(cb: OnAnimationActiveChangeCallback) {
    this.pushCallBack('animation-active-change', cb)
  }

  public setActiveRole(role: AiRole) {
    this.activeRole = role
  }

  public addElement(element: IAiConversationElement) {
    this.setActiveRole(element.role)
    this.elements.push(element)
  }

  public async getDataToBeProvidedToAi(): Promise<TAiConversationElementContent[]> {
    return []
  }

  public async getUserActionButtons(): Promise<AiActionButton[] | undefined | Error> {
    if (!this.config.userActions.actionButtons) {
      await this.loadAiUserActions()
    }
    return this.config.userActions.actionButtons
  }

  public async execUserActionButton(userAction: AiActionButton) {
    if (userAction.executed) {
      return
    }

    if (Array.isArray(this.config.userActions?.actionButtons)) {
      this.config.userActions.actionButtons?.map((a) => {
        if (a.action_id === userAction.action_id) {
          a.executed = true
        }

        return a
      })

      this.addElement({
        role: AiRole.user,
        content: [
          {
            content_type: 'text',
            text: userAction.action_name
          }
        ],
        noAnimation: true
      })
    }

    this.addElement(this.execAiAction(userAction))
  }

  protected execAiAction(action: AiActionButton): IAiConversationElement {
    return {
      role: AiRole.ai,
      content: this.getAiInferenceElement(action)
    }
  }

  protected async loadAiUserActions() {
    try {
      this.config.userActions.actionButtons = await this.api.getUserActions(this.templateId)
    } catch (e) {
      this.config.userActions.actionButtons = e as Error
    }
  }

  protected async getAiInferenceElement(
    action: AiServiceAction
  ): Promise<TAiConversationElementContent[]> {
    const contents: TAiConversationElementContent[] = []
    try {
      const res = await this.api.inference(action, this.data)

      for (const es of res.explanation_sections) {
        contents.push(es as MarkdownConversationElementContent)
      }
    } catch {
      contents.push({
        content_type: 'alert',
        variant: 'error',
        text: _t('Something went wrong. Please try again later.')
      })
    }

    return contents
  }

  protected getInitialElements(): IAiConversationElement[] {
    return []
  }

  private getPersistentRef(): Ref<boolean> {
    return usePersistentRef<boolean>(
      `ai-consent-${this.config.user_id}`,
      false,
      (v) => v as boolean,
      'local'
    )
  }
}
