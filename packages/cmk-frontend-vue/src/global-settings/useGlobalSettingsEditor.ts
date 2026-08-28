/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'
import { CmkError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, reactive, shallowRef } from 'vue'

import type { GlobalSettingsScope, GlobalSettingsService, ReceivedValue } from './api'

const { _t } = usei18n()

export interface EditorError {
  heading: TranslatedString
  message: TranslatedString
}

type SessionState = { type: 'busy' } | { type: 'ready' } | { type: 'failed'; error: EditorError }

export function describeError(error: unknown, fallback: TranslatedString): TranslatedString {
  if (error instanceof CmkError) {
    const context = error.getContext()
    return untranslated(context === '' ? error.message : `${error.message}\n\n${context}`)
  }
  return untranslated(`${fallback}\n\n${String(error)}`)
}

export function applyReceived(variable: GlobalSettingsVariable, received: ReceivedValue): void {
  variable.value = received.value
  variable.modified = !received.isDefault
}

export class EditorSession {
  private readonly editing: { received: ReceivedValue | null; state: SessionState } = reactive({
    received: null,
    state: { type: 'busy' }
  })

  constructor(
    readonly variable: GlobalSettingsVariable,
    private readonly service: GlobalSettingsService,
    private readonly scope: GlobalSettingsScope,
    private readonly requestClose: (session: EditorSession) => void
  ) {}

  get busy(): boolean {
    return this.editing.state.type === 'busy'
  }

  get editable(): boolean {
    return this.editing.state.type !== 'busy' && this.editing.received !== null
  }

  get error(): EditorError | null {
    return this.editing.state.type === 'failed' ? this.editing.state.error : null
  }

  async load(): Promise<void> {
    await this.runAction(_t('Loading failed'), async () => {
      this.storeReceived(await this.service.load(this.scope, this.variable.name))
    })
  }

  async save(value: unknown): Promise<void> {
    const received = this.editing.received
    if (received === null) {
      return
    }
    await this.runAction(_t('Saving failed'), async () => {
      this.storeReceived(
        await this.service.save(this.scope, this.variable.name, value, received.etag)
      )
      this.requestClose(this)
    })
  }

  async reset(): Promise<void> {
    const received = this.editing.received
    if (received === null) {
      return
    }
    await this.runAction(_t('Resetting failed'), async () => {
      await this.service.reset(this.scope, this.variable.name, received.etag)
      this.storeReceived(await this.service.load(this.scope, this.variable.name))
      this.requestClose(this)
    })
  }

  private async runAction(
    failureHeading: TranslatedString,
    action: () => Promise<void>
  ): Promise<void> {
    this.editing.state = { type: 'busy' }
    try {
      await action()
      this.editing.state = { type: 'ready' }
    } catch (error: unknown) {
      this.editing.state = {
        type: 'failed',
        error: {
          heading: failureHeading,
          message: describeError(error, _t('Could not reach the server.'))
        }
      }
    }
  }

  private storeReceived(received: ReceivedValue): void {
    this.editing.received = received
    applyReceived(this.variable, received)
  }
}

export function useGlobalSettingsEditor(
  service: GlobalSettingsService,
  scope: GlobalSettingsScope
): {
  session: Ref<EditorSession | null>
  openEditor: (variable: GlobalSettingsVariable) => Promise<void>
  closeEditor: () => void
} {
  const session = shallowRef<EditorSession | null>(null)

  function closeWhenCurrent(editorSession: EditorSession): void {
    if (session.value === editorSession) {
      session.value = null
    }
  }

  async function openEditor(variable: GlobalSettingsVariable): Promise<void> {
    const editorSession = new EditorSession(variable, service, scope, closeWhenCurrent)
    session.value = editorSession
    await editorSession.load()
  }

  function closeEditor(): void {
    session.value = null
  }

  return { session, openEditor, closeEditor }
}
