/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, expect, test, vi } from 'vitest'

import {
  isAnyCheatSheetVisible,
  isCheatSheetPinned,
  isCheatSheetVisible,
  subscribeAnyCheatSheetVisible,
  subscribeCheatSheetVisible,
  toggleCheatSheetPin
} from '@/lib/keyboard-cheat-sheet/cheatSheetKey'

const PINNED_STORAGE_KEY = 'keyboard-cheat-sheet-pinned'

/** The tracker is a page-lifetime singleton. */
afterEach(() => {
  vi.restoreAllMocks()
  releaseAlt()
  pressEscape()
  localStorage.clear()
})

function pressAltK(): void {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', altKey: true }))
}

function releaseK(): void {
  window.dispatchEvent(new KeyboardEvent('keyup', { key: 'k', altKey: true }))
}

function releaseAlt(): void {
  window.dispatchEvent(new KeyboardEvent('keyup', { key: 'Alt', altKey: false }))
}

function pressEscape(): void {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
}

function pinWithAltKK(): void {
  pressAltK()
  releaseK()
  pressAltK()
  releaseK()
  releaseAlt()
}

test('Alt+K shows the sheet for as long as Alt stays down', () => {
  const seen: boolean[] = []
  const unsubscribe = subscribeCheatSheetVisible((visible) => seen.push(visible))

  pressAltK()
  expect(isCheatSheetVisible()).toBe(true)
  releaseK()
  expect(isCheatSheetVisible()).toBe(true)
  releaseAlt()
  expect(isCheatSheetVisible()).toBe(false)

  expect(seen).toEqual([true, false])
  unsubscribe()
})

test('Alt on its own shows nothing', () => {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Alt', altKey: true }))

  expect(isCheatSheetVisible()).toBe(false)
})

test('a second K while Alt is still down pins the sheet', () => {
  pinWithAltKK()

  expect(isCheatSheetVisible()).toBe(true)
})

test('Esc lets a pinned sheet go', () => {
  pinWithAltKK()
  pressEscape()

  expect(isCheatSheetVisible()).toBe(false)
})

test('one more Alt+K lets a pinned sheet go once Alt is up again', () => {
  pinWithAltKK()

  pressAltK()
  expect(isCheatSheetVisible()).toBe(true)
  releaseK()
  releaseAlt()
  expect(isCheatSheetVisible()).toBe(false)
})

test('key repeat of a held K does not pin', () => {
  pressAltK()
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', altKey: true, repeat: true }))
  releaseAlt()

  expect(isCheatSheetVisible()).toBe(false)
})

test('losing the focus hides an unpinned sheet, because no keyup will arrive', () => {
  pressAltK()
  window.dispatchEvent(new Event('blur'))

  expect(isCheatSheetVisible()).toBe(false)
})

test('the pin is remembered, so the next page can bring the sheet back', async () => {
  pinWithAltKK()
  expect(localStorage.getItem(PINNED_STORAGE_KEY)).toBe('true')

  // What the next page does.
  vi.resetModules()
  const nextPage = await import('@/lib/keyboard-cheat-sheet/cheatSheetKey')
  expect(nextPage.isCheatSheetPinned()).toBe(true)
  expect(nextPage.isCheatSheetVisible()).toBe(true)
})

test('the pin can be toggled without touching the keyboard', () => {
  toggleCheatSheetPin()
  expect(isCheatSheetPinned()).toBe(true)
  expect(isCheatSheetVisible()).toBe(true)

  toggleCheatSheetPin()
  expect(isCheatSheetPinned()).toBe(false)
  expect(isCheatSheetVisible()).toBe(false)
})

test('a change is announced to the top window, for the key hints there', () => {
  const seen: boolean[] = []
  const unsubscribe = subscribeAnyCheatSheetVisible((visible) => seen.push(visible))

  pressAltK()
  expect(isAnyCheatSheetVisible()).toBe(true)
  releaseAlt()

  expect(seen).toEqual([true, false])
  unsubscribe()
})

test('a pin set by another frame holds here too', () => {
  localStorage.setItem(PINNED_STORAGE_KEY, 'true')
  window.dispatchEvent(new StorageEvent('storage', { key: PINNED_STORAGE_KEY }))

  expect(isCheatSheetPinned()).toBe(true)
  expect(isCheatSheetVisible()).toBe(true)
})

const HELD_MESSAGE = 'cmk-keyboard-cheat-sheet-held'

function tellHeldFromChildFrame(held: boolean): void {
  const frame = document.createElement('iframe')
  document.body.appendChild(frame)
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { source: HELD_MESSAGE, held },
      origin: window.location.origin,
      source: frame.contentWindow
    })
  )
  frame.remove()
}

test('Alt+K held in a nested frame shows the sheet here, without a pin', () => {
  const seen: boolean[] = []
  const unsubscribe = subscribeAnyCheatSheetVisible((visible) => seen.push(visible))

  tellHeldFromChildFrame(true)
  expect(isCheatSheetVisible()).toBe(true)
  expect(isCheatSheetPinned()).toBe(false)
  tellHeldFromChildFrame(false)
  expect(isCheatSheetVisible()).toBe(false)

  expect(seen).toEqual([true, false])
  unsubscribe()
})

test('messages from another origin or of another kind are ignored', () => {
  const frame = document.createElement('iframe')
  document.body.appendChild(frame)
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { source: HELD_MESSAGE, held: true },
      origin: 'https://other.example',
      source: frame.contentWindow
    })
  )
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { source: 'something-else', held: true },
      origin: window.location.origin,
      source: frame.contentWindow
    })
  )
  frame.remove()

  expect(isCheatSheetVisible()).toBe(false)
})

test('a nested frame hands Alt+K to its parent instead of announcing it to the top window', () => {
  const postMessage = vi.fn()
  vi.spyOn(window, 'parent', 'get').mockReturnValue({ postMessage } as unknown as Window)
  const seen: boolean[] = []
  const unsubscribe = subscribeAnyCheatSheetVisible((visible) => seen.push(visible))

  pressAltK()
  releaseAlt()

  expect(postMessage.mock.calls).toEqual([
    [{ source: HELD_MESSAGE, held: true }, window.location.origin],
    [{ source: HELD_MESSAGE, held: false }, window.location.origin]
  ])
  expect(seen).toEqual([])
  unsubscribe()
})
