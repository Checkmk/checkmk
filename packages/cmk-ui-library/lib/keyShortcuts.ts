/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { comboLabels, registerKeyboardHelp } from 'cmk-ui-library/lib/keyboardHelp'

import { randomId } from './randomId'

const { _t } = usei18n()

export type KeyShortcutHandlerCallback = (shortcut: KeyShortcut) => void

export interface KeyShortcutEnsured extends KeyShortcut {
  id: string
  key: string[]
  ctrl: boolean
  shift: boolean
  alt: boolean
  preventDefault: boolean
  propagate: boolean
}

export interface KeyShortcut {
  key: string[]
  ctrl?: boolean | undefined
  shift?: boolean | undefined
  alt?: boolean | undefined
  preventDefault?: boolean | undefined
  propagate?: boolean | undefined
  /** Cheat sheet group; "Other" if left out. */
  scope?: TranslatedString | undefined
  /** Cheat sheet text; listed as undocumented if left out. */
  description?: TranslatedString | undefined
}

export interface KeyShortcutHandler extends KeyShortcutEnsured {
  callback: KeyShortcutHandlerCallback
}

export interface KeyStates {
  [key: string]: boolean
}

const MODIFIER_KEYS = new Set([
  'control',
  'ctrl',
  'shift',
  'alt',
  'altgraph',
  'meta',
  'os',
  'super',
  'cmd',
  'command'
])

// Inputs that hold no text, so typing into them means nothing.
const NON_TEXT_INPUT_TYPES = new Set([
  'checkbox',
  'radio',
  'button',
  'submit',
  'reset',
  'range',
  'color',
  'file'
])

function isTextEntry(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  if (target.isContentEditable) {
    return true
  }
  if (target instanceof HTMLInputElement) {
    return !NON_TEXT_INPUT_TYPES.has(target.type)
  }
  return target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement
}

/**
 * A printable key with no Ctrl or Alt is a character before it is a shortcut, so whoever is
 * typing gets it. Escape, the arrows and the modified combinations stay with the shortcut,
 * because a text field is exactly where several of them are meant to work.
 */
function isBarePrintable(shortcut: KeyShortcutEnsured): boolean {
  return !shortcut.ctrl && !shortcut.alt && shortcut.key.every((key) => key.length === 1)
}

/** Modifiers first, then the keys - the order the cheat sheet shows them in. */
function shortcutCombo(shortcut: KeyShortcut): string[] {
  const combo: string[] = []
  if (shortcut.ctrl) {
    combo.push('Ctrl')
  }
  if (shortcut.shift) {
    combo.push('Shift')
  }
  if (shortcut.alt) {
    combo.push('Alt')
  }
  return combo.concat(shortcut.key)
}

export class KeyShortcutService {
  private keyStates: KeyStates = {}
  private handlers: KeyShortcutHandler[] = []
  private helpUnregisters = new Map<string, () => void>()
  private readonly boundHandleKeyDown: (e: KeyboardEvent) => void
  private readonly boundHandleKeyUp: (e: KeyboardEvent) => void
  private iframeObserver: MutationObserver | null = null

  constructor(
    private window: Window,
    private propagateTo: HTMLCollectionOf<HTMLIFrameElement> | null = null,
    private listenTo: HTMLCollectionOf<HTMLIFrameElement> | null = null
  ) {
    this.boundHandleKeyDown = this.handleKeyDown.bind(this)
    this.boundHandleKeyUp = this.handleKeyUp.bind(this)
    this.initListeners()
  }

  public on(shortcut: KeyShortcut, callback: KeyShortcutHandlerCallback): string {
    shortcut = this.ensureShortcut(shortcut)
    ;(shortcut as KeyShortcutHandler).callback = callback

    this.handlers.push(shortcut as KeyShortcutHandler)

    const id = (shortcut as KeyShortcutHandler).id
    this.helpUnregisters.set(
      id,
      registerKeyboardHelp([
        {
          kind: 'shortcut',
          scope: shortcut.scope ?? _t('Other'),
          combo: shortcutCombo(shortcut),
          description: shortcut.description
        }
      ])
    )
    return id
  }

  public remove(ids: string[]): void {
    for (const id of ids) {
      this.helpUnregisters.get(id)?.()
      this.helpUnregisters.delete(id)
    }
    this.handlers = this.handlers
      .map((handler) => {
        if (ids.indexOf(handler.id) >= 0) {
          return null
        } else {
          return handler
        }
      })
      .filter((handler) => handler !== null)
  }

  public setPropagateTo(propagateTo: HTMLCollectionOf<HTMLIFrameElement>): void {
    this.propagateTo = propagateTo
  }

  public static getShortCutCombo(shortcut: KeyShortcut): string[] {
    return shortcutCombo(shortcut)
  }

  public static getShortCutInfo(shortcut: KeyShortcut): string {
    return comboLabels(shortcutCombo(shortcut)).join(' + ')
  }

  private ensureShortcut(shortcut: KeyShortcut): KeyShortcutEnsured {
    const modifierKeys = shortcut.key.filter((key) => MODIFIER_KEYS.has(key.toLowerCase()))
    if (modifierKeys.length > 0) {
      throw new Error(
        `Modifier keys are not allowed in the shortcut "key" array: ${modifierKeys.join(', ')}. ` +
          'Use the "ctrl", "shift" or "alt" flags instead.'
      )
    }

    if (!shortcut.ctrl) {
      shortcut.ctrl = false
    }
    if (!shortcut.shift) {
      shortcut.shift = false
    }
    if (!shortcut.alt) {
      shortcut.alt = false
    }
    if (!shortcut.preventDefault) {
      shortcut.preventDefault = false
    }
    if (!shortcut.propagate) {
      shortcut.propagate = false
    }

    ;(shortcut as KeyShortcutEnsured).id = randomId()

    return shortcut as KeyShortcutEnsured
  }

  private initListeners() {
    this.window.addEventListener('keydown', this.boundHandleKeyDown)
    this.window.addEventListener('keyup', this.boundHandleKeyUp)

    if (this.listenTo) {
      this.observeIframes()
    }
  }

  private observeIframes(): void {
    for (let i = 0; i < this.listenTo!.length; i++) {
      const iframe = this.listenTo!.item(i)
      if (iframe) {
        this.listenToIframe(iframe)
      }
    }

    const body = this.window.document.body
    if (!body) {
      return
    }

    this.iframeObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node instanceof HTMLIFrameElement) {
            this.listenToIframe(node)
          } else if (node instanceof HTMLElement) {
            node.querySelectorAll('iframe').forEach((iframe) => this.listenToIframe(iframe))
          }
        }
      }
    })
    this.iframeObserver.observe(body, { childList: true, subtree: true })
  }

  private listenToIframe(iframe: HTMLIFrameElement): void {
    this.attachKeyListeners(iframe.contentWindow)
    iframe.addEventListener('load', () => this.attachKeyListeners(iframe.contentWindow))
  }

  private attachKeyListeners(contentWindow: Window | null): void {
    if (!contentWindow) {
      return
    }
    try {
      contentWindow.addEventListener('keydown', this.boundHandleKeyDown)
      contentWindow.addEventListener('keyup', this.boundHandleKeyUp)
    } catch {
      return
    }
  }

  private propagateEvent(e: KeyboardEvent) {
    if (this.propagateTo) {
      const eventClone = new KeyboardEvent(e.type, {
        key: e.key,
        ctrlKey: e.ctrlKey,
        altKey: e.altKey,
        shiftKey: e.shiftKey
      })

      for (let i = 0; i < this.propagateTo.length; i++) {
        this.propagateTo?.item(i)?.contentWindow?.dispatchEvent(eventClone)
      }
    }
  }

  private setKeyState(key: string, pressed: boolean): void {
    if (!key) {
      return
    }
    this.keyStates[key.toLowerCase()] = pressed
  }

  private handleKeyDown(e: KeyboardEvent): void {
    this.setKeyState(e.key, true)
    this.callHandlers(e)
  }

  private handleKeyUp(e: KeyboardEvent): void {
    this.setKeyState(e.key, false)
  }

  private shortcutKeysPressed(keys: string[]): boolean {
    for (const key of keys) {
      if (!key || !this.keyStates[key.toLowerCase()]) {
        return false
      }
    }

    return true
  }

  private callHandlers(e: KeyboardEvent): void {
    const typing = isTextEntry(e.target)
    for (const handler of this.handlers) {
      if (typing && isBarePrintable(handler)) {
        continue
      }
      if (
        e.ctrlKey === handler.ctrl &&
        e.shiftKey === handler.shift &&
        e.altKey === handler.alt &&
        this.shortcutKeysPressed(handler.key)
      ) {
        if (handler.preventDefault) {
          e.preventDefault()
        }
        if (handler.propagate) {
          this.propagateEvent(e)
        }
        handler.callback(handler)
      }
    }
  }
}

const keyShortcuts = new KeyShortcutService(window)

export function getKeyShortcutServiceInstance(
  propagateTo?: HTMLCollectionOf<HTMLIFrameElement>
): KeyShortcutService {
  if (propagateTo) {
    keyShortcuts.setPropagateTo(propagateTo)
  }
  return keyShortcuts
}
