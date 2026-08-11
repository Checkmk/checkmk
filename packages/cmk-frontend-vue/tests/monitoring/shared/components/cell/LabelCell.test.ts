/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, defineComponent, h, nextTick } from 'vue'

import { COLUMN_LAYOUT_KEY } from '@/monitoring/shared/components/MonitoringTableContext'
import LabelCell, { type LabelCellItem } from '@/monitoring/shared/components/cell/LabelCell.vue'

const TAG_WIDTH = 100
const OVERFLOW_BASE_WIDTH = 20
const OVERFLOW_WIDTH_PER_CHARACTER = 10

/** The "+X" button grows with its label, the way a real one does. */
function overflowWidth(element: Element): number {
  return (
    OVERFLOW_BASE_WIDTH + (element.textContent ?? '').trim().length * OVERFLOW_WIDTH_PER_CHARACTER
  )
}

/**
 * jsdom does no layout, so every measured element reports zero. Hand each tag a fixed width and
 * lay them out left to right, with the overflow button behind the last one, mirroring the single
 * non-wrapping row the cell measures in.
 */
function stubLayout(rowWidth: number): void {
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
    configurable: true,
    get(this: HTMLElement) {
      return this.classList.contains('monitoring-label-cell__row') ? rowWidth : 0
    }
  })
  HTMLElement.prototype.getBoundingClientRect = function (this: HTMLElement): DOMRect {
    const row = this.closest('.monitoring-label-cell__row')
    if (this === row) {
      return { left: 0, right: rowWidth, width: rowWidth } as DOMRect
    }
    const measured = Array.from(
      row?.querySelectorAll('[data-label-cell-item], [data-label-cell-overflow]') ?? []
    )
    const index = measured.indexOf(this)
    if (index === -1) {
      return { left: 0, right: 0, width: 0 } as DOMRect
    }
    const left = index * TAG_WIDTH
    const width = this.hasAttribute('data-label-cell-overflow') ? overflowWidth(this) : TAG_WIDTH
    return { left, right: left + width, width } as DOMRect
  }
}

function makeItems(count: number): LabelCellItem[] {
  return Array.from({ length: count }, (_unused, index) => ({
    text: `cmk/label_${index}: value` as TranslatedString
  }))
}

async function mountCell(items: LabelCellItem[], rowWidth: number) {
  stubLayout(rowWidth)
  const rendered = render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(LabelCell, { items, columnId: 'labels' })])])])
      }
    })
  )
  await nextTick()
  await nextTick()
  return rendered
}

function visibleTags(container: Element): Element[] {
  return Array.from(container.querySelectorAll('[data-label-cell-item]'))
}

test('shows every entry when they all fit the column', async () => {
  const { container } = await mountCell(makeItems(2), 500)

  expect(visibleTags(container)).toHaveLength(2)
  expect(screen.queryByRole('button', { name: /Show all/ })).not.toBeInTheDocument()
})

test('collapses the entries that do not fit into a "+X" button', async () => {
  const { container } = await mountCell(makeItems(5), 250)

  expect(visibleTags(container)).toHaveLength(2)
  expect(screen.getByRole('button', { name: 'Show all 5 entries' })).toHaveTextContent('+3')
})

test('shows all entries once the "+X" button is pressed', async () => {
  const { container } = await mountCell(makeItems(5), 250)

  await userEvent.click(screen.getByRole('button', { name: 'Show all 5 entries' }))

  expect(visibleTags(container)).toHaveLength(5)
  expect(screen.getByRole('button', { name: 'show less' })).toBeInTheDocument()
})

test('collapses again via "show less"', async () => {
  const { container } = await mountCell(makeItems(5), 250)

  await userEvent.click(screen.getByRole('button', { name: 'Show all 5 entries' }))
  await userEvent.click(screen.getByRole('button', { name: 'show less' }))

  expect(visibleTags(container)).toHaveLength(2)
})

test('keeps one entry rendered when not even that one fits, with the full text as its tooltip', async () => {
  const { container } = await mountCell(makeItems(3), 20)

  const tags = visibleTags(container)
  expect(tags).toHaveLength(1)
  expect(tags[0]).toHaveAttribute('title', 'cmk/label_0: value')
})

test('reserves room for the widest "+X" the button can end up showing', async () => {
  // 20 entries of 100px in a 345px row. The button ends up reading "+18", a digit wider than the
  // "+0" it shows while measuring - reserving only the narrow placeholder's width leaves the
  // button hanging over the row's edge, where the row's overflow:hidden clips its label.
  const { container } = await mountCell(makeItems(20), 345)

  const button = container.querySelector('[data-label-cell-overflow]')!
  const row = container.querySelector('.monitoring-label-cell__row')!
  expect(button.getBoundingClientRect().right).toBeLessThanOrEqual(
    row.getBoundingClientRect().right
  )
  expect(button).toHaveTextContent(`+${20 - visibleTags(container).length}`)
})

test('takes the available width from the table column layout when there is one', async () => {
  stubLayout(500)
  const layout = computed(
    () =>
      new Map([
        [
          'labels',
          {
            // 500px row plus the cell padding the layout reports for the whole column
            width: 516,
            pinnedLeft: null,
            pinnedRight: null,
            isLastPinned: false,
            isFirstPinnedRight: false,
            justify: 'left' as const
          }
        ]
      ])
  )
  const { container } = render(
    defineComponent({
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(LabelCell, { items: makeItems(3), columnId: 'labels' })])])
        ])
      }
    }),
    { global: { provide: { [COLUMN_LAYOUT_KEY as symbol]: layout } } }
  )
  await nextTick()
  await nextTick()

  expect(visibleTags(container)).toHaveLength(3)
})
