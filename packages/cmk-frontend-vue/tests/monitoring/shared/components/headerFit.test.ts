/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { headerFitWidth, sortButtonFitWidth } from '@/monitoring/shared/components/headerFit'

// jsdom does no layout, so the cell, label and text widths are stubbed per test.
function layOut(widths: { cell: number; label: number; text: number; labelPadding?: number }): {
  cell: HTMLElement
  label: HTMLElement
} {
  const cell = document.createElement('th')
  const label = document.createElement('span')
  label.textContent = 'Mode'
  label.style.paddingLeft = `${widths.labelPadding ?? 0}px`
  cell.append(label)
  vi.spyOn(cell, 'getBoundingClientRect').mockReturnValue({ width: widths.cell } as DOMRect)
  vi.spyOn(label, 'getBoundingClientRect').mockReturnValue({ width: widths.label } as DOMRect)
  vi.spyOn(document, 'createRange').mockReturnValue({
    selectNodeContents: () => {},
    getBoundingClientRect: () => ({ width: widths.text }) as DOMRect
  } as unknown as Range)
  return { cell, label }
}

afterEach(() => {
  vi.restoreAllMocks()
})

test('a truncated label needs the room around it plus its full text', () => {
  const { cell, label } = layOut({ cell: 56, label: 24, text: 34 })

  expect(headerFitWidth(cell, label)).toBe(66)
})

test('the label padding counts as room around the text', () => {
  const { cell, label } = layOut({ cell: 56, label: 32, text: 34, labelPadding: 8 })

  expect(headerFitWidth(cell, label)).toBe(66)
})

test('a label with room to spare needs only its text', () => {
  const { cell, label } = layOut({ cell: 120, label: 88, text: 34 })

  expect(headerFitWidth(cell, label)).toBe(66)
})

test('a fractional width is rounded up so the text still fits', () => {
  const { cell, label } = layOut({ cell: 56.4, label: 24.4, text: 33.2 })

  expect(headerFitWidth(cell, label)).toBe(66)
})

test('a cell that is not laid out yet reports nothing', () => {
  const { cell, label } = layOut({ cell: 0, label: 0, text: 0 })

  expect(headerFitWidth(cell, label)).toBeNull()
})

// jsdom does no layout, so the widths of the cell, the button and its items are stubbed per test.
function layOutSortButton(widths: {
  cell: number
  button: number
  text: number
  sortIcon?: number
  gap: number
}): { cell: HTMLElement; button: HTMLElement; label: HTMLElement } {
  const cell = document.createElement('th')
  const button = document.createElement('button')
  button.style.columnGap = `${widths.gap}px`
  const label = document.createElement('span')
  label.textContent = 'State age'
  button.append(label)
  cell.append(button)
  vi.spyOn(cell, 'getBoundingClientRect').mockReturnValue({ width: widths.cell } as DOMRect)
  vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({ width: widths.button } as DOMRect)
  vi.spyOn(label, 'getBoundingClientRect').mockReturnValue({ width: 20 } as DOMRect)
  if (widths.sortIcon !== undefined) {
    const sortIcon = document.createElement('div')
    button.append(sortIcon)
    vi.spyOn(sortIcon, 'getBoundingClientRect').mockReturnValue({
      width: widths.sortIcon
    } as DOMRect)
  }
  vi.spyOn(document, 'createRange').mockReturnValue({
    selectNodeContents: () => {},
    getBoundingClientRect: () => ({ width: widths.text }) as DOMRect
  } as unknown as Range)
  return { cell, button, label }
}

test('a sort button needs the room around it plus its full text and its other items', () => {
  const { cell, button, label } = layOutSortButton({
    cell: 100,
    button: 84,
    text: 60,
    sortIcon: 10,
    gap: 4
  })

  expect(sortButtonFitWidth(cell, button, label)).toBe(90)
})

test('a sort button that is not laid out yet reports nothing', () => {
  const { cell, button, label } = layOutSortButton({ cell: 0, button: 0, text: 0, gap: 4 })

  expect(sortButtonFitWidth(cell, button, label)).toBeNull()
})
