/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, test, vi } from 'vitest'

import { focusLeftElement } from '@/components/date-time/focusLeftElement'

afterEach(() => {
  vi.restoreAllMocks()
})

function dispatchFocusOut(current: HTMLElement, relatedTarget: EventTarget | null): boolean {
  let left = false
  current.addEventListener('focusout', (event) => {
    left = focusLeftElement(event)
  })
  current.dispatchEvent(new FocusEvent('focusout', { bubbles: true, relatedTarget }))
  return left
}

describe('focusLeftElement', () => {
  test('relatedTarget inside ⇒ false', () => {
    const container = document.createElement('div')
    const child = document.createElement('input')
    container.appendChild(child)
    expect(dispatchFocusOut(container, child)).toBe(false)
  })

  test('relatedTarget outside ⇒ true', () => {
    const container = document.createElement('div')
    const outside = document.createElement('button')
    expect(dispatchFocusOut(container, outside)).toBe(true)
  })

  test('null target + window blurred ⇒ false', () => {
    vi.spyOn(document, 'hasFocus').mockReturnValue(false)
    const container = document.createElement('div')
    expect(dispatchFocusOut(container, null)).toBe(false)
  })

  test('null target + window focused ⇒ true', () => {
    vi.spyOn(document, 'hasFocus').mockReturnValue(true)
    const container = document.createElement('div')
    expect(dispatchFocusOut(container, null)).toBe(true)
  })
})
