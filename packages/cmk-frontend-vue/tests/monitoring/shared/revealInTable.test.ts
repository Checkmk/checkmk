/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterAll, beforeAll, beforeEach, expect, test, vi } from 'vitest'

import { revealInTable } from '@/monitoring/shared/revealInTable'

const originalRect = Element.prototype.getBoundingClientRect

// jsdom does no layout: elements are placed by their `data-rect`, "left top width height".
beforeAll(() => {
  Element.prototype.getBoundingClientRect = function (this: Element): DOMRect {
    const [left = 0, top = 0, width = 0, height = 0] = (this.getAttribute('data-rect') ?? '')
      .split(' ')
      .map(Number)
    return new DOMRect(left, top, width, height)
  }
})

afterAll(() => {
  Element.prototype.getBoundingClientRect = originalRect
})

/** A 300×200 viewport; a 20px sticky header; a 50px column pinned to either side. */
function table(targetRect: string, pinned = false): { scroller: HTMLElement; target: HTMLElement } {
  const scroller = document.createElement('div')
  scroller.setAttribute('data-rect', '0 0 300 200')
  Object.defineProperty(scroller, 'clientWidth', { value: 300 })
  Object.defineProperty(scroller, 'clientHeight', { value: 200 })
  scroller.scrollBy = vi.fn() as unknown as HTMLElement['scrollBy']
  scroller.innerHTML = `
    <table>
      <thead data-rect="0 0 300 20"><tr><th><button>header</button></th></tr></thead>
      <tbody><tr>
        <td style="position: sticky" data-rect="0 0 50 20"></td>
        <td ${pinned ? 'style="position: sticky"' : ''}><button id="target" data-rect="${targetRect}"></button></td>
        <td style="position: sticky" data-rect="250 0 50 20"></td>
      </tr></tbody>
    </table>`
  document.body.replaceChildren(scroller)
  return { scroller, target: scroller.querySelector<HTMLElement>('#target')! }
}

beforeEach(() => {
  document.body.replaceChildren()
})

test('a cell behind the sticky header is scrolled down below it', () => {
  const { scroller, target } = table('100 10 40 20')

  revealInTable(target, scroller)

  expect(scroller.scrollBy).toHaveBeenCalledWith({ top: -10, left: 0 })
})

test('a cell behind a pinned column is scrolled out from under it', () => {
  const { scroller, target } = table('30 50 40 20')

  revealInTable(target, scroller)

  expect(scroller.scrollBy).toHaveBeenCalledWith({ top: 0, left: -20 })
})

test('a cell behind the right pinned column is scrolled out from under it', () => {
  const { scroller, target } = table('230 50 40 20')

  revealInTable(target, scroller)

  expect(scroller.scrollBy).toHaveBeenCalledWith({ top: 0, left: 20 })
})

test('a pinned cell is only scrolled vertically', () => {
  const { scroller, target } = table('30 190 40 20', true)

  revealInTable(target, scroller)

  expect(scroller.scrollBy).toHaveBeenCalledWith({ top: 10, left: 0 })
})

test('a header cell is not scrolled vertically', () => {
  const { scroller } = table('100 50 40 20')
  const header = scroller.querySelector<HTMLElement>('th button')!
  header.setAttribute('data-rect', '100 0 40 20')

  revealInTable(header, scroller)

  expect(scroller.scrollBy).toHaveBeenCalledWith({ top: 0, left: 0 })
})
