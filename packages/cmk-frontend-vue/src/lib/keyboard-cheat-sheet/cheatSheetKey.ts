/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Alt+K shows the keyboard cheat sheet (CMK-38372) while Alt stays down, a second K pins
 * it, and Esc, one more Alt+K or the pin lets it go. Tracked from page load so the sheet
 * can be fetched lazily; the pin is kept in localStorage so it survives page changes.
 * Every change is also announced to the top window, where the main menu's key hints follow
 * the sheet of whichever frame has the keyboard.
 */
import { storageHandler } from 'cmk-ui-library/lib/utils'
import { type Ref, onBeforeUnmount, ref } from 'vue'

type Subscriber = (state: boolean) => void

const PINNED_STORAGE_KEY = 'keyboard-cheat-sheet-pinned'
const VISIBLE_EVENT = 'cmk-keyboard-cheat-sheet-visible'

const visibleSubscribers = new Set<Subscriber>()
const pinSubscribers = new Set<Subscriber>()
let tracking = false
let altDown = false
/** K presses during the current Alt hold. */
let presses = 0
let pinned = readPinned()
let visible = pinned

function readPinned(): boolean {
  try {
    return storageHandler.get(localStorage, PINNED_STORAGE_KEY, false) === true
  } catch {
    return false
  }
}

function setPinned(next: boolean): void {
  if (next === pinned) {
    return
  }
  pinned = next
  try {
    storageHandler.set(localStorage, PINNED_STORAGE_KEY, next)
  } catch {
    // Private window or full storage: the pin still holds for this page.
  }
  for (const subscriber of pinSubscribers) {
    subscriber(pinned)
  }
  publish()
}

function publish(): void {
  const next = (altDown && presses > 0) || pinned
  if (next === visible) {
    return
  }
  visible = next
  for (const subscriber of visibleSubscribers) {
    subscriber(visible)
  }
  announce()
}

function announce(): void {
  try {
    window.top?.dispatchEvent(new CustomEvent<boolean>(VISIBLE_EVENT, { detail: visible }))
  } catch {
    // A top window of another origin has no key hints to follow.
  }
}

export function isCheatSheetKey(event: KeyboardEvent): boolean {
  return event.altKey && event.key.toLowerCase() === 'k'
}

function onKeyDown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    setPinned(false)
    return
  }
  if (!event.altKey) {
    return
  }
  altDown = true
  if (!isCheatSheetKey(event) || event.repeat) {
    return
  }
  presses += 1
  // One Alt+K lets a pinned sheet go, a second K pins it (again).
  setPinned(presses > 1)
  publish()
}

function onKeyUp(event: KeyboardEvent): void {
  // Another key of the combination let go while Alt is still down.
  if (event.altKey) {
    return
  }
  altDown = false
  presses = 0
  publish()
}

/** The pin of another frame or tab. */
function onStorage(event: StorageEvent): void {
  if (event.key === PINNED_STORAGE_KEY) {
    setPinned(readPinned())
  }
}

/** No keyup arrives once the focus is gone. */
function onBlur(): void {
  altDown = false
  presses = 0
  publish()
}

function startTracking(): void {
  if (tracking) {
    return
  }
  tracking = true
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
  window.addEventListener('blur', onBlur)
  window.addEventListener('storage', onStorage)
}

export function isCheatSheetVisible(): boolean {
  return visible
}

export function isCheatSheetPinned(): boolean {
  return pinned
}

export function toggleCheatSheetPin(): void {
  setPinned(!pinned)
}

/** Last announced by any frame, this one included; the top window only. */
let anyVisible = visible

export function isAnyCheatSheetVisible(): boolean {
  return anyVisible
}

export function subscribeAnyCheatSheetVisible(subscriber: Subscriber): () => void {
  startTracking()
  const listener = (event: Event): void => {
    anyVisible = (event as CustomEvent<boolean>).detail
    subscriber(anyVisible)
  }
  window.addEventListener(VISIBLE_EVENT, listener)
  return () => {
    window.removeEventListener(VISIBLE_EVENT, listener)
  }
}

export function subscribeCheatSheetVisible(subscriber: Subscriber): () => void {
  startTracking()
  visibleSubscribers.add(subscriber)
  return () => {
    visibleSubscribers.delete(subscriber)
  }
}

function useSubscribed(subscribers: Set<Subscriber>, current: boolean): Ref<boolean> {
  const state = ref(current)
  const subscriber: Subscriber = (next) => {
    state.value = next
  }
  startTracking()
  subscribers.add(subscriber)
  onBeforeUnmount(() => {
    subscribers.delete(subscriber)
  })
  return state
}

export function useCheatSheetVisible(): Ref<boolean> {
  return useSubscribed(visibleSubscribers, visible)
}

export function useCheatSheetPinned(): Ref<boolean> {
  return useSubscribed(pinSubscribers, pinned)
}
