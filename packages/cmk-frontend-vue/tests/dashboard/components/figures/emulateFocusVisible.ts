/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type MockInstance, afterEach, beforeEach, vi } from 'vitest'

/**
 * jsdom never matches `:focus-visible`. Like a browser, this counts focus as the keyboard's unless
 * a pointer was pressed after the last key.
 */
export function emulateFocusVisible(): void {
  let spy: MockInstance<Element['matches']> | undefined
  let pointerLast = false
  const pointerPressed = () => {
    pointerLast = true
  }
  const keyPressed = () => {
    pointerLast = false
  }
  beforeEach(() => {
    pointerLast = false
    document.addEventListener('pointerdown', pointerPressed, true)
    document.addEventListener('keydown', keyPressed, true)
    const matches = Element.prototype.matches
    spy = vi.spyOn(Element.prototype, 'matches').mockImplementation(function (
      this: Element,
      selector: string
    ) {
      return selector === ':focus-visible'
        ? this === document.activeElement && !pointerLast
        : matches.call(this, selector)
    })
  })
  afterEach(() => {
    document.removeEventListener('pointerdown', pointerPressed, true)
    document.removeEventListener('keydown', keyPressed, true)
    spy?.mockRestore()
  })
}
