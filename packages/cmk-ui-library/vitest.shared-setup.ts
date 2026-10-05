/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup } from '@testing-library/vue'
import { afterAll, afterEach, vi } from 'vitest'

window.HTMLElement.prototype.scrollIntoView = function () {}
window.HTMLElement.prototype.showPopover = function () {}
window.HTMLElement.prototype.hasPointerCapture = () => false
window.HTMLElement.prototype.setPointerCapture = () => {}
window.HTMLElement.prototype.releasePointerCapture = () => {}

// d3-timer keeps the requestAnimationFrame it imported; a frame requested under fake timers dies
// with the fake clock and stalls d3 for the rest of the worker.
const { setTimeout: realSetTimeout, clearTimeout: realClearTimeout } = globalThis
window.requestAnimationFrame = (callback) =>
  Number(realSetTimeout(() => callback(performance.now()), 1000 / 60))
window.cancelAnimationFrame = (handle) => realClearTimeout(handle)

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  // The key shortcut service outlives the test and takes a key sent without keyup as held
  window.dispatchEvent(new FocusEvent('blur'))
  Reflect.deleteProperty(navigator, 'clipboard')
  localStorage.clear()
  sessionStorage.clear()
  document.body.replaceChildren()
  document.body.getAttributeNames().forEach((name) => document.body.removeAttribute(name))
  window.history.replaceState(null, '', '/')
})

afterAll(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})
