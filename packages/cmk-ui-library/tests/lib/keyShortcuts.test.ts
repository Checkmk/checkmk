/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type KeyShortcut, KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { type KeyboardHelpEntry, getKeyboardHelp } from 'cmk-ui-library/lib/keyboardHelp'
import { afterEach, expect, test, vi } from 'vitest'

const shortcuts = new KeyShortcutService(window)
let registered: string[] = []

function t(value: string): TranslatedString {
  return value as TranslatedString
}

function entriesOf(scope: string): KeyboardHelpEntry[] {
  return getKeyboardHelp().filter((entry) => entry.scope === scope)
}

function on(shortcut: KeyShortcut): ReturnType<typeof vi.fn> {
  const callback = vi.fn()
  registered.push(shortcuts.on(shortcut, callback))
  return callback
}

function element<T extends HTMLElement>(html: string): T {
  const host = document.createElement('div')
  host.innerHTML = html
  document.body.appendChild(host)
  return host.firstElementChild as T
}

/** Returns whether the shortcut swallowed the key. */
function press(target: HTMLElement, key: string, init: KeyboardEventInit = {}): boolean {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init })
  target.dispatchEvent(event)
  // The service remembers which keys are down, so release it before the next press.
  target.dispatchEvent(new KeyboardEvent('keyup', { key, bubbles: true, ...init }))
  return event.defaultPrevented
}

afterEach(() => {
  shortcuts.remove(registered)
  registered = []
  document.body.innerHTML = ''
})

test('a bare printable shortcut leaves the character to whoever is typing', () => {
  const focusSearch = on({ key: ['/'], preventDefault: true })
  const input = element<HTMLInputElement>('<input type="text" />')

  const swallowed = press(input, '/')

  expect(focusSearch).not.toHaveBeenCalled()
  expect(swallowed).toBe(false)
})

test('a textarea and a select count as typing as well', () => {
  const focusSearch = on({ key: ['/'], preventDefault: true })

  press(element<HTMLTextAreaElement>('<textarea></textarea>'), '/')
  press(element<HTMLSelectElement>('<select></select>'), '/')

  expect(focusSearch).not.toHaveBeenCalled()
})

test('it still fires from an input holding no text, and from anything else', () => {
  const focusSearch = on({ key: ['/'], preventDefault: true })

  press(element<HTMLInputElement>('<input type="checkbox" />'), '/')
  press(element<HTMLButtonElement>('<button type="button"></button>'), '/')

  expect(focusSearch).toHaveBeenCalledTimes(2)
})

test('the keys a text field is meant to share still fire', () => {
  const escape = on({ key: ['Escape'] })
  const up = on({ key: ['ArrowUp'] })
  const ctrlK = on({ key: ['k'], ctrl: true })
  const input = element<HTMLInputElement>('<input type="text" />')

  press(input, 'Escape')
  press(input, 'ArrowUp')
  press(input, 'k', { ctrlKey: true })

  expect(escape).toHaveBeenCalledTimes(1)
  expect(up).toHaveBeenCalledTimes(1)
  expect(ctrlK).toHaveBeenCalledTimes(1)
})

test('a shortcut is on the cheat sheet from on() until remove()', () => {
  const service = new KeyShortcutService(window)
  const id = service.on(
    { key: ['k'], alt: true, scope: t('Main menu'), description: t('Toggle key hints') },
    () => {}
  )

  expect(entriesOf('Main menu')).toEqual([
    { kind: 'shortcut', scope: 'Main menu', combo: ['Alt', 'k'], description: 'Toggle key hints' }
  ])

  service.remove([id])
  expect(entriesOf('Main menu')).toEqual([])
})

test('a shortcut without scope and description is listed as undocumented under "Other"', () => {
  const service = new KeyShortcutService(window)
  const id = service.on({ key: ['Enter'], ctrl: true }, () => {})

  expect(entriesOf('Other')).toEqual([
    { kind: 'shortcut', scope: 'Other', combo: ['Ctrl', 'Enter'], description: undefined }
  ])
  service.remove([id])
})

test('handing the same shortcut object to on() twice keeps both entries apart', () => {
  // ServiceBase.enableShortCuts() reuses the object.
  const service = new KeyShortcutService(window)
  const shortcut = { key: ['/'], ctrl: true, scope: t('Sidebar') }
  const first = service.on(shortcut, () => {})
  const second = service.on(shortcut, () => {})
  expect(entriesOf('Sidebar')).toHaveLength(2)

  service.remove([first])
  expect(entriesOf('Sidebar')).toHaveLength(1)

  service.remove([second])
  expect(entriesOf('Sidebar')).toHaveLength(0)
})

test('getShortCutInfo spells out the modifiers', () => {
  expect(KeyShortcutService.getShortCutInfo({ key: ['h'], alt: true })).toBe('Alt + H')
  expect(KeyShortcutService.getShortCutInfo({ key: ['k'], ctrl: true, shift: true })).toBe(
    'Ctrl + Shift + K'
  )
})
