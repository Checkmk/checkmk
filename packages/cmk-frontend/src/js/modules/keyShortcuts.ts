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

export interface KeyStates {
  [key: string]: boolean
}

export class KeyShortcutService {
  private keyStates: KeyStates = {}
  private handlers: KeyShortcutHandler[] = []

  constructor(
    private window: Window,
    private propagateTo: HTMLCollectionOf<HTMLIFrameElement> | null = null
  ) {
    this.window.addEventListener('keydown', this.handleKeyDown.bind(this))
    this.window.addEventListener('keyup', this.handleKeyUp.bind(this))
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

  private setKeyState(key: string, pressed: boolean): void {
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
      if (!this.keyStates[key.toLowerCase()]) {
        return false
      }
    }

    return true
  }

  private callHandlers(e: KeyboardEvent): void {
    for (const handler of this.handlers) {
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
