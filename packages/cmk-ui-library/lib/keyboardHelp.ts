/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Registry behind the keyboard cheat sheet (CMK-38372). Three kinds of entries:
 * `shortcut` (page-level, from `KeyShortcutService.on()`), `widget` (keys a focused
 * component handles itself, via `useWidgetKeys()`) and `hint` (a sentence with the keys
 * inline as `[Key]`, via `useKeyboardHints()`). The composables release their entries
 * with the calling component.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, onScopeDispose, readonly, ref } from 'vue'

const { _t } = usei18n()

export type KeyboardHelpKind = 'shortcut' | 'widget' | 'hint'

export interface KeyboardHelpEntry {
  kind: KeyboardHelpKind
  scope: TranslatedString
  /** `Ctrl`, `Shift`, `Alt` first, then `KeyboardEvent.key` values; empty for hints. */
  combo: string[]
  /** Undefined: listed as undocumented. */
  description: TranslatedString | undefined
}

export interface WidgetKey {
  combo: string[]
  description: TranslatedString
}

const registrations = new Map<number, readonly KeyboardHelpEntry[]>()
const subscribers = new Set<() => void>()
let sequence = 0

function notify(): void {
  for (const subscriber of subscribers) {
    subscriber()
  }
}

export function registerKeyboardHelp(entries: readonly KeyboardHelpEntry[]): () => void {
  const id = ++sequence
  registrations.set(id, entries)
  notify()
  return () => {
    if (registrations.delete(id)) {
      notify()
    }
  }
}

export function getKeyboardHelp(): KeyboardHelpEntry[] {
  return [...registrations.values()].flat()
}

export function subscribeKeyboardHelp(callback: () => void): () => void {
  subscribers.add(callback)
  return () => {
    subscribers.delete(callback)
  }
}

export function useWidgetKeys(scope: TranslatedString, keys: readonly WidgetKey[]): void {
  onScopeDispose(
    registerKeyboardHelp(keys.map((key): KeyboardHelpEntry => ({ kind: 'widget', scope, ...key })))
  )
}

/** Keys inline as `[Key]`, e.g. `Press [/] to search`. */
export function useKeyboardHints(
  scope: TranslatedString,
  hints: readonly TranslatedString[]
): void {
  onScopeDispose(
    registerKeyboardHelp(
      hints.map(
        (hint): KeyboardHelpEntry => ({ kind: 'hint', scope, combo: [], description: hint })
      )
    )
  )
}

const highlighted = ref<string | null>(null)

/** The combination under the pointer, on a key hint or a cheat sheet row, as `comboKey()` gives it. */
export const highlightedCombo: Readonly<Ref<string | null>> = readonly(highlighted)

export function comboKey(combo: readonly string[]): string {
  return comboLabels(combo).join('+')
}

export function highlightCombo(combo: readonly string[] | null): void {
  highlighted.value = combo ? comboKey(combo) : null
}

/** One `CmkKeyboardKey` label per key: its symbol names for the glyph keys, short names for the rest. */
export function comboLabels(combo: readonly string[]): string[] {
  return combo.map(keyLabel)
}

function keyLabel(key: string): string {
  switch (key.toLowerCase()) {
    case 'ctrl':
    case 'control':
      return _t('Ctrl')
    case 'shift':
      return _t('Shift')
    case 'alt':
      return _t('Alt')
    case 'arrowup':
      return 'arrow-up'
    case 'arrowdown':
      return 'arrow-down'
    case 'arrowleft':
      return 'arrow-left'
    case 'arrowright':
      return 'arrow-right'
    case 'enter':
      return 'enter'
    case 'backspace':
      return 'backspace'
    case 'escape':
      return _t('Esc')
    case ' ':
    case 'space':
    case 'spacebar':
      return _t('Space')
    case 'tab':
      return _t('Tab')
    case 'delete':
      return _t('Del')
    case 'home':
      return _t('Home')
    case 'end':
      return _t('End')
    case 'pageup':
      return _t('PgUp')
    case 'pagedown':
      return _t('PgDn')
    case 'contextmenu':
      return _t('Menu')
    default:
      return key.length === 1 ? key.toUpperCase() : key
  }
}
