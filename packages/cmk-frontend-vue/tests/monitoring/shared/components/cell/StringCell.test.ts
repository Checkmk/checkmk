/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'

function mountCell(value: string | undefined, props: Record<string, unknown> = {}) {
  return render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(StringCell, { value, ...props })])])])
      }
    })
  )
}

test('renders the value as cell text', () => {
  mountCell('web-1')

  expect(screen.getByTitle('web-1')).toBeInTheDocument()
})

test('repeats no value on hover that fits the cell, when told to title only a cut one', async () => {
  mountCell('fe80::1', { titleOnlyWhenCut: true })

  await fireEvent.mouseEnter(screen.getByText('fe80::1'))

  expect(screen.queryByTitle('fe80::1')).not.toBeInTheDocument()
})

test('shows a cut value in full on hover, when told to title only a cut one', async () => {
  mountCell('fe80::1', { titleOnlyWhenCut: true })
  const text = screen.getByText('fe80::1')
  Object.defineProperty(text, 'scrollWidth', { configurable: true, value: 120 })
  Object.defineProperty(text, 'clientWidth', { configurable: true, value: 40 })

  await fireEvent.mouseEnter(text)

  expect(text).toHaveAttribute('title', 'fe80::1')
})

test('renders a placeholder instead of crashing when the value is missing', () => {
  const { container } = mountCell(undefined)

  const cell = container.querySelector('td')
  expect(cell).not.toBeNull()
  expect(cell).toHaveTextContent('n/a')
})

test('leaves a state marker as written unless the cell shows plugin output', () => {
  const { container } = mountCell('load: 3.1(!)')

  expect(container.querySelector('.cmk-tag')).toBeNull()
  expect(container.querySelector('td')).toHaveTextContent('(!)')
})

test('renders the state markers of plugin output as badges', () => {
  const { container } = mountCell('load: 3.1(!)', { stateMarkers: true })

  expect(container.querySelector('.cmk-state-tag--warning')).toHaveTextContent('WA')
})

test('renders a button and forwards its click when the button prop is set', async () => {
  const onClick = vi.fn()
  const { container } = render(
    defineComponent({
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(StringCell, { value: 'web-1', button: true, onClick })])])
        ])
      }
    })
  )

  const button = container.querySelector('button')
  expect(button).not.toBeNull()
  await fireEvent.click(button!)
  expect(onClick).toHaveBeenCalledTimes(1)
})
