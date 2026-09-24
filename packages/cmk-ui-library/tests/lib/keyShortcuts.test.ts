/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type KeyShortcut, KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { afterEach, expect, test, vi } from 'vitest'

const service = new KeyShortcutService(window)
let registered: string[] = []

function on(shortcut: KeyShortcut): ReturnType<typeof vi.fn> {
  const callback = vi.fn()
  registered.push(service.on(shortcut, callback))
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
  service.remove(registered)
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
