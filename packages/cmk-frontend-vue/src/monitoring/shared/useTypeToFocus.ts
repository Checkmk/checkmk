/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Type to focus (CMK-38372).
 *
 * Idle, a printable key nothing else binds starts a search: the first clickable element in
 * `scope` whose text contains the buffer gets the focus. Searching, the buffer owns the
 * keyboard: every printable key is typed into it, `/` and Space included, Down/Right and
 * Up/Left move between the matches, Backspace edits, the page's own shortcuts stay quiet
 * and the browser's keys pass. A search is abandoned by Esc or a pointer going down
 * anywhere, and the focus ring goes with it. It is finished by Enter or a click activating
 * the match, or by the focus leaving the view; the focus then stays where it landed. All
 * matches are framed while searching.
 */
import { getKeyboardHelp } from 'cmk-ui-library/lib/keyboardHelp'
import { type Ref, onBeforeUnmount, onMounted, readonly, ref } from 'vue'

import { isCheatSheetKey } from '@/lib/keyboard-cheat-sheet/cheatSheetKey'

import { INTERACTIVE_SELECTOR } from './interactiveSelector'
import { isTextEntry } from './isTextEntry'

/** Framed by `TypeToFocusIndicator.vue`; the focused one keeps the ordinary focus ring. */
export const MATCH_ATTRIBUTE = 'data-type-to-focus-match'
const NEXT_KEYS = new Set(['ArrowDown', 'ArrowRight'])
const PREVIOUS_KEYS = new Set(['ArrowUp', 'ArrowLeft'])

export interface TypeToFocus {
  buffer: Readonly<Ref<string>>
  /** -1 while nothing matches. */
  index: Readonly<Ref<number>>
  count: Readonly<Ref<number>>
}

/** Cells soft-break their text with zero-width spaces; those must not break a match. */
function normalise(text: string | null | undefined): string {
  return (text ?? '')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

/** Visible-text matches first, label-only matches second, each in DOM order. */
function findMatches(scope: HTMLElement, needle: string): HTMLElement[] {
  const hidden = new Map<HTMLElement, boolean>()
  const isHidden = (node: HTMLElement): boolean => {
    let value = hidden.get(node)
    if (value === undefined) {
      value = window.getComputedStyle(node).display === 'none'
      hidden.set(node, value)
    }
    return value
  }
  const isVisible = (element: HTMLElement): boolean => {
    if (
      element.closest('[aria-hidden="true"]') ||
      window.getComputedStyle(element).visibility === 'hidden'
    ) {
      return false
    }
    for (
      let node: HTMLElement | null = element;
      node && node !== scope;
      node = node.parentElement
    ) {
      if (isHidden(node)) {
        return false
      }
    }
    return true
  }

  const byText: HTMLElement[] = []
  const byLabel: HTMLElement[] = []
  for (const element of scope.querySelectorAll<HTMLElement>(INTERACTIVE_SELECTOR)) {
    if (!isVisible(element)) {
      continue
    }
    if (normalise(element.textContent).includes(needle)) {
      byText.push(element)
    } else if (
      normalise(`${element.getAttribute('aria-label') ?? ''} ${element.title}`).includes(needle)
    ) {
      byLabel.push(element)
    }
  }
  return byText.concat(byLabel)
}

/** The combination as the help registry lists it, lower-cased: modifiers first, then the key. */
function comboOf(event: KeyboardEvent): string[] {
  const combo: string[] = []
  if (event.ctrlKey) {
    combo.push('ctrl')
  }
  if (event.shiftKey) {
    combo.push('shift')
  }
  if (event.altKey) {
    combo.push('alt')
  }
  combo.push(event.key.toLowerCase())
  return combo
}

function isRegistered(combo: string[], kinds: readonly string[]): boolean {
  return getKeyboardHelp().some(
    (entry) =>
      kinds.includes(entry.kind) &&
      entry.combo.length === combo.length &&
      entry.combo.every((key, position) => key.toLowerCase() === combo[position])
  )
}

/** Bound on its own by a page shortcut or a widget, like `/`; must not start a search. */
function isBoundKey(key: string): boolean {
  return isRegistered([key.toLowerCase()], ['shortcut', 'widget'])
}

/** A page shortcut with modifiers, like Alt+K. */
function isPageShortcut(event: KeyboardEvent): boolean {
  return isRegistered(comboOf(event), ['shortcut'])
}

/** Ours alone: nothing else on the page gets to see this key. */
function claim(event: KeyboardEvent): void {
  event.preventDefault()
  event.stopImmediatePropagation()
}

export function useTypeToFocus(scope: Readonly<Ref<HTMLElement | null>>): TypeToFocus {
  const buffer = ref('')
  const index = ref(-1)
  const count = ref(0)
  /** The focused match. */
  let match: HTMLElement | null = null
  let marked: HTMLElement[] = []

  function mark(matches: HTMLElement[]): void {
    for (const element of marked) {
      element.removeAttribute(MATCH_ATTRIBUTE)
    }
    for (const element of matches) {
      element.setAttribute(MATCH_ATTRIBUTE, '')
    }
    marked = matches
  }

  function reset(): void {
    mark([])
    buffer.value = ''
    index.value = -1
    count.value = 0
    match = null
  }

  /** Abandoned: the focus ring goes too. */
  function abort(): void {
    if (match && document.activeElement === match) {
      match.blur()
    }
    reset()
  }

  /** Fulfilled, or something else took over: the focus stays where it is. */
  function finish(): void {
    reset()
  }

  /** `step` 0 restarts at the first match; the matches are re-read, rows come and go. */
  function jump(step: -1 | 0 | 1): void {
    const matches = scope.value ? findMatches(scope.value, buffer.value.toLowerCase()) : []
    count.value = matches.length
    mark(matches)
    if (matches.length === 0) {
      index.value = -1
      match = null
      return
    }
    const position = match ? matches.indexOf(match) : -1
    index.value =
      step === 0 || position < 0 ? 0 : (position + step + matches.length) % matches.length
    match = matches[index.value] ?? null
    match?.scrollIntoView({ block: 'nearest' })
    match?.focus({ preventScroll: true })
  }

  /** Idle: only an unbound printable key starts a search, everything else keeps its meaning. */
  function onIdleKey(event: KeyboardEvent): void {
    if (event.ctrlKey || event.altKey || event.metaKey || event.repeat) {
      return
    }
    if (event.key.length !== 1 || event.key === ' ' || isBoundKey(event.key)) {
      return
    }
    claim(event)
    buffer.value = event.key
    jump(0)
  }

  /** Searching: the buffer owns the keyboard. */
  function onSearchKey(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      claim(event)
      abort()
      return
    }
    if (event.key === 'Enter' && !match) {
      claim(event)
      return
    }
    if (event.key === 'Enter') {
      finish()
      return
    }
    if (event.ctrlKey || event.altKey || event.metaKey) {
      if (isPageShortcut(event) && !isCheatSheetKey(event)) {
        claim(event)
      }
      return
    }
    if (NEXT_KEYS.has(event.key) || PREVIOUS_KEYS.has(event.key)) {
      claim(event)
      jump(NEXT_KEYS.has(event.key) ? 1 : -1)
      return
    }
    if (event.key === 'Backspace') {
      claim(event)
      buffer.value = buffer.value.slice(0, -1)
      if (buffer.value) {
        jump(0)
      } else {
        abort()
      }
      return
    }
    if (event.key.length === 1) {
      claim(event)
      if (!event.repeat) {
        buffer.value += event.key
        jump(0)
      }
    }
  }

  function onKeyDown(event: KeyboardEvent): void {
    if (event.isComposing || isTextEntry(event.target)) {
      return
    }
    const active = document.activeElement
    if (active && active !== document.body && !scope.value?.contains(active)) {
      return
    }
    if (buffer.value) {
      onSearchKey(event)
    } else {
      onIdleKey(event)
    }
  }

  /** Space would still click the match on the way up. */
  function onKeyUp(event: KeyboardEvent): void {
    if (buffer.value && event.key === ' ' && !isTextEntry(event.target)) {
      claim(event)
    }
  }

  function onPointerDown(): void {
    abort()
  }

  /** Assistive technology activates a match with a click alone, no key or pointer event. */
  function onClick(): void {
    finish()
  }

  /** E.g. into a slide-in the match has opened. */
  function onFocusIn(event: FocusEvent): void {
    if (buffer.value && event.target instanceof Node && !scope.value?.contains(event.target)) {
      finish()
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', onKeyDown, true)
    window.addEventListener('keyup', onKeyUp, true)
    document.addEventListener('pointerdown', onPointerDown, true)
    document.addEventListener('click', onClick, true)
    document.addEventListener('focusin', onFocusIn)
  })

  onBeforeUnmount(() => {
    mark([])
    window.removeEventListener('keydown', onKeyDown, true)
    window.removeEventListener('keyup', onKeyUp, true)
    document.removeEventListener('pointerdown', onPointerDown, true)
    document.removeEventListener('click', onClick, true)
    document.removeEventListener('focusin', onFocusIn)
  })

  return { buffer: readonly(buffer), index: readonly(index), count: readonly(count) }
}
