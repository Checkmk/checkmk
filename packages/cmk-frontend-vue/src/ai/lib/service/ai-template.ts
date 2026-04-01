/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ExplainThisIssueData, Legal } from 'cmk-shared-typing/typescript/ai_button'
import { type Ref, nextTick, reactive, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { KeyShortcutService } from '@/lib/keyShortcuts'
import { ServiceBase } from '@/lib/service/base'
import usePersistentRef from '@/lib/usePersistentRef'

import { type ButtonProps } from '@/components/CmkButton.vue'

import {
  AiApiClient,
  type AiServiceAction,
  type InfoResponse,
  RateLimitError,
  type StreamEvent
} from '@/ai/lib/ai-api-client'
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
  context_data?: T
  conversationId?: string | undefined
  getDisclaimer?: () => Promise<TAiConversationElementContent[]> | undefined
  userActions: IAiUserActionConfig
}

export type TBaseConversationElementEmits = { done: [] }

export interface BaseConversationElementContent {
  content_type: string
  title?: string | undefined
  noAnimation?: boolean | undefined
}

export interface SystemContextConversationElementContent extends BaseConversationElementContent {
  content_type: 'system_context'
  host_name: string
  host_state: ExplainThisIssueData['host_state']
  service_name?: string
  service_state?: ExplainThisIssueData['service_state']
  is_stale?: boolean
  [key: string]: unknown
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

export interface RateLimitConversationElementContent extends BaseConversationElementContent {
  content_type: 'rate_limit'
}

export type TAiConversationElementContent =
  | AlertConversationElementContent
  | CodeBlockConversationElementContent
  | DialogConversationElementContent
  | ImageConversationElementContent
  | ListConversationElementContent
  | MarkdownConversationElementContent
  | RateLimitConversationElementContent
  | TextConversationElementContent
  | SystemContextConversationElementContent

export interface IAiConversationElement {
  role: AiRole
  content: TAiConversationElementContent[]
  noAnimation?: boolean | undefined
  hideControls?: boolean | undefined
  loadingText?: string | undefined
  error?: string | undefined
  displayed?: boolean | undefined
  streaming?: boolean | undefined
}

export type OnAnimationActiveChangeCallback = (active: boolean) => void

export class AiTemplateService extends ServiceBase {
  public conversationOpen = ref(false)
  public elements = reactive<IAiConversationElement[]>([])
  public config: IAiConversationConfig<unknown>
  public activeRole: AiRole = AiRole.user
  public info: InfoResponse | null = null
  protected api: AiApiClient
  private streamAbortController: AbortController | null = null

  constructor(
    public templateId: string,
    public userId: string,
    public context_data: ExplainThisIssueData,
    siteName: string,
    public legal: Legal
  ) {
    super(templateId, new KeyShortcutService(window))

    this.api = new AiApiClient(siteName)
    this.config = {
      user_id: this.userId,
      context_data: this.context_data,
      userActions: {}
    }

    void this.loadInfo()

    this.addContext()
  }

  public isDisclaimerShown(): boolean {
    return this.getDisclaimerPersistentRef().value
  }

  public persistDisclaimerShown() {
    const disclaimerShown = this.getDisclaimerPersistentRef()
    disclaimerShown.value = true

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

  public markElementDisplayed(index: number) {
    if (this.elements[index]) {
      this.elements[index]!.displayed = true
    }
  }

  public disableAllAnimations() {
    this.elements.forEach((element) => {
      if (element.displayed) {
        element.noAnimation = true
      }
    })

    // Ensure active role is set correctly - if the last element is displayed, role should be user
    if (this.elements.length > 0) {
      const lastElement = this.elements[this.elements.length - 1]!
      if (lastElement.displayed) {
        this.setActiveRole(AiRole.user)
      }
    }
  }

  public addContext() {
    const { is_stale: isStale } = this.context_data as ExplainThisIssueData & { is_stale?: boolean }
    this.addElement({
      role: AiRole.system,
      content: [
        {
          content_type: 'system_context',
          host_name: this.context_data.host_name,
          host_state: this.context_data.host_state,
          service_name: this.context_data.service_name,
          service_state: this.context_data.service_state,
          ...(isStale !== undefined && { is_stale: isStale })
        }
      ],
      noAnimation: true,
      displayed: true
    })

    this.setActiveRole(AiRole.user)
  }

  public async getUserActionButtons(): Promise<AiActionButton[] | undefined | Error> {
    if (!this.config.userActions.actionButtons) {
      await this.loadAiUserActions()
    }
    return this.config.userActions.actionButtons
  }

  public async execUserActionButton(userAction: AiActionButton) {
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
        noAnimation: true,
        displayed: true
      })
    }

    this.addElement(this.execAiAction(userAction))
  }

  public refreshUserActionButton(userAction: AiActionButton) {
    const refreshedAiElement = this.execAiAction(userAction)

    for (let i = this.elements.length - 1; i >= 0; i--) {
      if (this.elements[i]?.role === AiRole.ai) {
        this.setActiveRole(refreshedAiElement.role)
        this.elements.splice(i, 1, refreshedAiElement)
        return
      }
    }

    this.addElement(refreshedAiElement)
  }

  public onInfoLoaded(cb: () => void) {
    this.pushCallBack('info-loaded', cb)
  }

  protected toSentenceCase(str: string): string {
    return String(str).charAt(0).toUpperCase() + String(str).slice(1)
  }

  protected async loadInfo() {
    this.info = await this.api.getInfo()
    this.dispatchCallback('info-loaded')
  }

  protected execAiAction(action: AiActionButton): IAiConversationElement {
    this.streamAbortController?.abort()
    this.streamAbortController = new AbortController()
    const { signal } = this.streamAbortController

    const contents = ref<TAiConversationElementContent[]>([])

    const element: IAiConversationElement = {
      role: AiRole.ai,
      content: contents.value,
      noAnimation: true,
      streaming: true,
      displayed: true
    }

    const {
      host_name: hostName,
      host_state: hostState,
      service_name: serviceName,
      service_state: serviceState
    } = this.context_data
    const contextForAi = {
      host_name: hostName,
      host_state: hostState,
      service_name: serviceName,
      ...(serviceState !== 'Pending' && { service_state: serviceState })
    }

    void this.api.streamInference(
      action,
      contextForAi,
      (event: StreamEvent) => {
        if (!event?.type) {
          return
        }
        switch (event.type) {
          case 'metadata':
            break
          case 'finish':
            break

          case 'thinking':
            contents.value.push({
              content_type: 'markdown',
              content: event.text,
              title: event.type
            } as MarkdownConversationElementContent)
            break

          case 'answer': {
            const lastItem = contents.value[contents.value.length - 1]
            if (lastItem?.title === 'answer' && lastItem.content_type === 'markdown') {
              // Append to existing answer chunk
              ;(lastItem as MarkdownConversationElementContent).content += event.text
            } else {
              // Create new answer chunk
              contents.value.push({
                content_type: 'markdown',
                content: event.text,
                title: event.type
              } as MarkdownConversationElementContent)
            }
            break
          }
        }
      },
      async (_error: Error) => {
        if (signal.aborted) {
          return
        }
        if (_error instanceof RateLimitError) {
          contents.value.push({
            content_type: 'rate_limit'
          } as RateLimitConversationElementContent)
        } else {
          contents.value.push({
            content_type: 'alert',
            variant: 'error',
            text: _t('Something went wrong. Please try again later.')
          } as AlertConversationElementContent)
        }
        await nextTick()
        element.streaming = false
        element.noAnimation = false
      },
      () => {
        element.streaming = false
        element.noAnimation = false
      },
      signal
    )

    return element
  }

  protected async loadAiUserActions() {
    try {
      this.config.userActions.actionButtons = await this.api.getUserActions(this.templateId)
    } catch (e) {
      this.config.userActions.actionButtons = e as Error
    }
  }

  protected getInitialElements(): IAiConversationElement[] {
    return []
  }

  private getDisclaimerPersistentRef(): Ref<boolean> {
    return usePersistentRef<boolean>(
      `ai-disclaimer-${this.config.user_id}`,
      false,
      (v) => v as boolean,
      'local'
    )
  }
}
