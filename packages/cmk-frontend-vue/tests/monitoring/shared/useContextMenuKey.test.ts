/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import { useContextMenuKey } from '@/monitoring/shared/useContextMenuKey'

const opened = vi.fn()

function onTriggerKey(event: KeyboardEvent): void {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    opened((event.target as HTMLElement).textContent)
  }
}

const fixture = defineComponent({
  setup() {
    const root = ref<HTMLElement | null>(null)
    useContextMenuKey(root)
    return () =>
      h('div', [
        h('button', { type: 'button' }, 'outside'),
        h('table', { ref: root }, [
          h('tbody', [
            h('tr', [
              h('td', [h('button', { type: 'button' }, 'host name')]),
              h('td', [h('input', { type: 'text', 'aria-label': 'comment' })]),
              h('td', [h('button', { type: 'button', 'aria-expanded': 'false' }, 'expand labels')]),
              h('td', [
                h(
                  'button',
                  { type: 'button', 'aria-haspopup': 'menu', onKeydown: onTriggerKey },
                  'more'
                )
              ])
            ]),
            h('tr', [h('td', [h('button', { type: 'button' }, 'no menu')])])
          ])
        ])
      ])
  }
})

function press(target: HTMLElement, init: KeyboardEventInit): KeyboardEvent {
  target.focus()
  const event = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, ...init })
  target.dispatchEvent(event)
  return event
}

test('the Menu key opens the menu of the focused row, and keeps the browser menu shut', () => {
  render(fixture)
  opened.mockReset()

  const event = press(screen.getByRole('button', { name: 'host name' }), { key: 'ContextMenu' })
  const contextmenu = new MouseEvent('contextmenu', { bubbles: true, cancelable: true })
  document.activeElement?.dispatchEvent(contextmenu)

  expect(event.defaultPrevented).toBe(true)
  expect(contextmenu.defaultPrevented).toBe(true)
  expect(opened).toHaveBeenCalledExactlyOnceWith('more')
  expect(screen.getByRole('button', { name: 'more' })).toHaveFocus()
})

test('Shift+F10 does the same, a collapsible cell is no menu', () => {
  render(fixture)
  opened.mockReset()

  press(screen.getByRole('button', { name: 'expand labels' }), { key: 'F10', shiftKey: true })

  expect(opened).toHaveBeenCalledExactlyOnceWith('more')
})

test('without a menu in reach the key is left to the browser', () => {
  render(fixture)
  opened.mockReset()

  const inRow = press(screen.getByRole('button', { name: 'no menu' }), { key: 'ContextMenu' })
  const outside = press(screen.getByRole('button', { name: 'outside' }), { key: 'ContextMenu' })

  expect(inRow.defaultPrevented).toBe(false)
  expect(outside.defaultPrevented).toBe(false)
  expect(opened).not.toHaveBeenCalled()
})

test('in a text field the key is left to the browser', () => {
  render(fixture)
  opened.mockReset()

  const event = press(screen.getByRole('textbox', { name: 'comment' }), { key: 'ContextMenu' })

  expect(event.defaultPrevented).toBe(false)
  expect(opened).not.toHaveBeenCalled()
})

test('the menu can cancel the ArrowDown it is sent', () => {
  render(fixture)
  const arrowDowns: KeyboardEvent[] = []
  const record = (event: KeyboardEvent): void => {
    if (event.key === 'ArrowDown') {
      arrowDowns.push(event)
    }
  }
  window.addEventListener('keydown', record)

  press(screen.getByRole('button', { name: 'host name' }), { key: 'ContextMenu' })
  window.removeEventListener('keydown', record)

  expect(arrowDowns.map((event) => event.defaultPrevented)).toEqual([true])
})

test('letting go of Shift before F10 does not keep the browser menu shut', async () => {
  render(fixture)
  press(screen.getByRole('button', { name: 'host name' }), { key: 'F10', shiftKey: true })
  window.dispatchEvent(new KeyboardEvent('keyup', { key: 'Shift' }))
  window.dispatchEvent(new KeyboardEvent('keyup', { key: 'F10' }))
  await new Promise((resolve) => setTimeout(resolve, 0))

  const contextmenu = new MouseEvent('contextmenu', { bubbles: true, cancelable: true })
  document.body.dispatchEvent(contextmenu)

  expect(contextmenu.defaultPrevented).toBe(false)
})

test('only the next browser menu is kept shut', () => {
  render(fixture)
  press(screen.getByRole('button', { name: 'host name' }), { key: 'ContextMenu' })
  document.body.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }))

  const second = new MouseEvent('contextmenu', { bubbles: true, cancelable: true })
  document.body.dispatchEvent(second)

  expect(second.defaultPrevented).toBe(false)
})
