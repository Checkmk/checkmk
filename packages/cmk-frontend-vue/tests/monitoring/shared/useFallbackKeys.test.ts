/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { afterAll, beforeAll, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { useFallbackKeys } from '@/monitoring/shared/useFallbackKeys'

const scrollBy = vi.fn()
const scrollTo = vi.fn()
const originalRect = Element.prototype.getBoundingClientRect

// jsdom does no layout: elements are placed by their `data-rect`, "left top".
beforeAll(() => {
  Element.prototype.scrollBy = scrollBy as unknown as Element['scrollBy']
  Element.prototype.scrollTo = scrollTo as unknown as Element['scrollTo']
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.getBoundingClientRect = function (this: Element): DOMRect {
    const [left, top] = (this.getAttribute('data-rect') ?? '0 0').split(' ').map(Number)
    const size = this.hasAttribute('data-rect') ? 20 : 0
    return new DOMRect(left, top, size, size)
  }
})

afterAll(() => {
  Element.prototype.getBoundingClientRect = originalRect
})

/** A two by two grid of cells, a search field and an outsider. */
const fixture = defineComponent({
  setup() {
    const root = ref<HTMLElement | null>(null)
    const table = ref<HTMLElement | null>(null)
    useFallbackKeys(root, () => table.value)
    const cell = (name: string, rect: string) =>
      h('button', { type: 'button', 'data-rect': rect }, name)
    return () =>
      h('div', [
        h('button', { type: 'button', 'data-rect': '500 500' }, 'outside'),
        h('div', { ref: root }, [
          h('input', { type: 'text', 'aria-label': 'Search', 'data-rect': '0 -50' }),
          h('div', { ref: table, 'data-testid': 'table' }, [
            cell('a1', '0 0'),
            cell('b1', '100 0'),
            cell('a2', '0 40'),
            cell('b2', '100 40')
          ])
        ])
      ])
  }
})

function button(name: string): HTMLElement {
  return screen.getByRole('button', { name })
}

function press(key: string, init: KeyboardEventInit = {}): KeyboardEvent {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init })
  ;(document.activeElement ?? document.body).dispatchEvent(event)
  return event
}

test('the arrows move the focus to the nearest element in their direction', () => {
  render(fixture)
  button('a1').focus()

  press('ArrowDown')
  expect(button('a2')).toHaveFocus()
  press('ArrowRight')
  expect(button('b2')).toHaveFocus()
  press('ArrowUp')
  expect(button('b1')).toHaveFocus()
  press('ArrowLeft')
  expect(button('a1')).toHaveFocus()
})

test('at the edge, in a field and on a key taken already the focus stays put', () => {
  render(fixture)
  button('a2').focus()
  expect(press('ArrowDown').defaultPrevented).toBe(false)
  expect(button('a2')).toHaveFocus()

  const field = screen.getByRole('textbox', { name: 'Search' })
  field.focus()
  press('ArrowDown')
  expect(field).toHaveFocus()

  button('a1').focus()
  const taken = (event: Event): void => event.preventDefault()
  button('a1').addEventListener('keydown', taken)
  press('ArrowDown')
  button('a1').removeEventListener('keydown', taken)
  press('ArrowDown', { shiftKey: true })
  expect(button('a1')).toHaveFocus()
})

test('with nothing focused ArrowUp/ArrowDown scroll the table', () => {
  render(fixture)
  scrollBy.mockReset()
  ;(document.activeElement as HTMLElement | null)?.blur()

  press('ArrowDown')
  press('ArrowUp')

  expect(scrollBy.mock.calls.map(([options]) => Math.sign(options.top))).toEqual([1, -1])
})

test('with nothing focused the paging keys scroll the table a page, Home and End to its ends', () => {
  render(fixture)
  scrollBy.mockReset()
  scrollTo.mockReset()
  Object.defineProperty(screen.getByTestId('table'), 'scrollHeight', { value: 1000 })
  ;(document.activeElement as HTMLElement | null)?.blur()

  press('PageDown')
  press('PageUp')
  press('End')
  press('Home')

  expect(scrollBy.mock.calls.map(([options]) => Math.sign(options.top))).toEqual([1, -1])
  expect(scrollTo.mock.calls.map(([options]) => options.top)).toEqual([1000, 0])
})

test('the paging keys leave a focused element to the browser', () => {
  render(fixture)
  scrollBy.mockReset()
  scrollTo.mockReset()
  button('a1').focus()

  expect(press('PageDown').defaultPrevented).toBe(false)
  expect(press('End').defaultPrevented).toBe(false)
  expect(scrollBy).not.toHaveBeenCalled()
  expect(scrollTo).not.toHaveBeenCalled()
})

test('Esc lets go of the focus, unless its handling moved the focus already', () => {
  render(fixture)
  button('b2').focus()
  press('Escape')
  expect(document.body).toHaveFocus()

  const handled = (): void => button('a1').focus()
  button('b2').focus()
  button('b2').addEventListener('keydown', handled)
  press('Escape')
  button('b2').removeEventListener('keydown', handled)
  expect(button('a1')).toHaveFocus()
})

test('the outside is none of its business', () => {
  render(fixture)
  button('outside').focus()

  press('ArrowUp')
  press('Escape')

  expect(button('outside')).toHaveFocus()
})
