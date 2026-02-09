/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type KeyShortcutHandlerCallback = (shortcut: KeyShortcut) => void

export interface KeyShortcutEnsured extends KeyShortcut {
  key: string[]
  ctrl: boolean
  shift: boolean
  alt: boolean
  preventDefault: boolean
  propagate: boolean
}

export interface KeyShortcut {
  key: string[]
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  preventDefault?: boolean
  propagate?: boolean
}

export interface KeyShortcutHandler extends KeyShortcutEnsured {
  callback: KeyShortcutHandlerCallback
}

const MODIFIER_KEYS = ['Control', 'Shift', 'Alt']
const N_KEYS_REMEMBERED = 10

export class KeyShortcutService {
  private keySequence: string[] = []
  private handlers: KeyShortcutHandler[] = []

  constructor(
    private window: Window,
    private propagateTo: HTMLCollectionOf<HTMLIFrameElement> | null = null
  ) {
    this.window.addEventListener('keydown', this.handleKeyDown.bind(this))
  }

  public on(shortcut: KeyShortcut, callback: KeyShortcutHandlerCallback): void {
    shortcut = this.ensureShortcut(shortcut)
    ;(shortcut as KeyShortcutHandler).callback = callback

    this.handlers.push(shortcut as KeyShortcutHandler)
  }

  public setPropagateTo(propagateTo: HTMLCollectionOf<HTMLIFrameElement>): void {
    this.propagateTo = propagateTo
  }

  private ensureShortcut(shortcut: KeyShortcut): KeyShortcutEnsured {
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

    return shortcut as KeyShortcutEnsured
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

  private recordKeyPress(key: string): void {
    const newSize = this.keySequence.push(key)
    if (newSize > N_KEYS_REMEMBERED) {
      this.keySequence.shift()
    }
  }

  private handleKeyDown(e: KeyboardEvent): void {
    if (MODIFIER_KEYS.includes(e.key)) {
      return
    }
    this.recordKeyPress(e.key.toLowerCase())
    this.callHandlers(e)
  }

  private sequenceMatches(keys: string[]): boolean {
    const startIndex = this.keySequence.length - keys.length
    if (startIndex < 0) {
      return false
    }
    return keys.every((key, index) => key === this.keySequence[startIndex + index])
  }

  private callHandlers(e: KeyboardEvent): void {
    for (const handler of this.handlers) {
      if (
        e.ctrlKey === handler.ctrl &&
        e.shiftKey === handler.shift &&
        e.altKey === handler.alt &&
        this.sequenceMatches(handler.key)
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
