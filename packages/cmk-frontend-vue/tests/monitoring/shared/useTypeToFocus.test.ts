/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { registerKeyboardHelp } from 'cmk-ui-library/lib/keyboardHelp'
import { afterEach, expect, test, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import { MATCH_ATTRIBUTE, useTypeToFocus } from '@/monitoring/shared/useTypeToFocus'

function t(value: string): TranslatedString {
  return value as TranslatedString
}

const clicks = vi.fn()

/** A view in miniature: matches by text, by label only, hidden ones, and one outsider. */
const fixture = defineComponent({
  setup() {
    const root = ref<HTMLElement | null>(null)
    const state = useTypeToFocus(root)
    return () =>
      h('div', [
        h('button', { type: 'button' }, 'cpu outside'),
        h('div', { ref: root }, [
          h('button', { type: 'button', role: 'checkbox', 'aria-label': 'Select host cpunode' }),
          h('button', { type: 'button', onClick: clicks }, 'cpunode'),
          h('button', { type: 'button', onClick: clicks }, 'CPU load'),
          h('button', { type: 'button', 'aria-label': 'Filter CPU' }),
          h('button', { type: 'button', hidden: true }, 'cpuhidden'),
          h('button', { type: 'button', style: { display: 'none' } }, 'cpushown'),
          h('button', { type: 'button' }, 'dbnode'),
          h('button', { type: 'button' }, 'cpu-\u200Bnode'),
          h('input', { type: 'text', 'aria-label': 'Search' }),
          h(
            'output',
            { 'data-testid': 'state' },
            `${state.buffer.value}|${state.index.value}|${state.count.value}`
          )
        ])
      ])
  }
})

afterEach(() => {
  clicks.mockReset()
})

async function state(): Promise<string> {
  await nextTick()
  return screen.getByTestId('state').textContent ?? ''
}

function button(name: string | RegExp): HTMLElement {
  return screen.getByRole('button', { name })
}

/** Whether a keydown is taken by the search: prevented, and kept from every other listener. */
function claimed(init: KeyboardEventInit): boolean {
  const others = vi.fn()
  window.addEventListener('keydown', others)
  const event = new KeyboardEvent('keydown', { ...init, bubbles: true, cancelable: true })
  document.body.dispatchEvent(event)
  window.removeEventListener('keydown', others)
  expect(others).toHaveBeenCalledTimes(event.defaultPrevented ? 0 : 1)
  return event.defaultPrevented
}

test('typing focuses the first element whose text contains the letters, case-insensitively', async () => {
  render(fixture)

  await userEvent.keyboard('cpu')

  expect(button('cpunode')).toHaveFocus()
  expect(await state()).toBe('cpu|0|5')
})

test('a text match beats a label-only match, then Down and Right walk on and wrap', async () => {
  render(fixture)
  await userEvent.keyboard('cpu')

  await userEvent.keyboard('{ArrowDown}')
  expect(button('CPU load')).toHaveFocus()
  await userEvent.keyboard('{ArrowRight}')
  expect(button(/cpu-.node/)).toHaveFocus()
  await userEvent.keyboard('{ArrowDown}')
  expect(screen.getByRole('checkbox', { name: 'Select host cpunode' })).toHaveFocus()
  await userEvent.keyboard('{ArrowDown}')
  expect(button('Filter CPU')).toHaveFocus()
  await userEvent.keyboard('{ArrowDown}')
  expect(button('cpunode')).toHaveFocus()
  expect(await state()).toBe('cpu|0|5')
})

test('Up and Left walk back and wrap', async () => {
  render(fixture)
  await userEvent.keyboard('cpu')

  await userEvent.keyboard('{ArrowUp}')
  expect(button('Filter CPU')).toHaveFocus()
  await userEvent.keyboard('{ArrowLeft}')
  expect(screen.getByRole('checkbox', { name: 'Select host cpunode' })).toHaveFocus()
  expect(await state()).toBe('cpu|3|5')
})

test('hidden elements are never matches', async () => {
  render(fixture)

  await userEvent.keyboard('cpuhidden')
  expect(await state()).toBe('cpuhidden|-1|0')
  await userEvent.keyboard('{Escape}')

  await userEvent.keyboard('cpushown')
  expect(await state()).toBe('cpushown|-1|0')
})

test('zero-width spaces in the text do not break a match', async () => {
  render(fixture)

  await userEvent.keyboard('cpu-n')

  expect(button(/cpu-.node/)).toHaveFocus()
  expect(await state()).toBe('cpu-n|0|1')
})

test('Backspace shortens the buffer and searches again; emptying it ends the search', async () => {
  render(fixture)
  await userEvent.keyboard('dbn')
  expect(button('dbnode')).toHaveFocus()

  await userEvent.keyboard('{Backspace}{Backspace}')
  expect(await state()).toBe('d|0|5')

  await userEvent.keyboard('{Backspace}')
  expect(await state()).toBe('|-1|0')
  expect(document.body).toHaveFocus()
})

test('Escape ends the search, drops the focus ring and hands the arrow keys back', async () => {
  render(fixture)
  await userEvent.keyboard('cpu')
  expect(claimed({ key: 'ArrowDown' })).toBe(true)

  await userEvent.keyboard('{Escape}')

  expect(await state()).toBe('|-1|0')
  expect(document.body).toHaveFocus()
  expect(claimed({ key: 'ArrowDown' })).toBe(false)
})

test('Enter activates the match and ends the search, the focus stays on it', async () => {
  render(fixture)
  await userEvent.keyboard('cpu')

  await userEvent.keyboard('{Enter}')

  expect(clicks).toHaveBeenCalledTimes(1)
  expect(await state()).toBe('|-1|0')
  expect(button('cpunode')).toHaveFocus()
})

test('Enter without a match activates nothing and keeps the search on', async () => {
  render(fixture)
  await userEvent.keyboard('cpux')

  await userEvent.keyboard('{Enter}')

  expect(clicks).not.toHaveBeenCalled()
  expect(await state()).toBe('cpux|-1|0')
})

test('the focus leaving the view ends the search, e.g. into what the match opened', async () => {
  render(fixture)
  await userEvent.keyboard('cpu')

  button('cpu outside').focus()

  expect(await state()).toBe('|-1|0')
  expect(button('cpu outside')).toHaveFocus()
  expect(claimed({ key: 'Escape' })).toBe(false)
})

test('a click on the match, however it was produced, ends the search', async () => {
  render(fixture)
  await userEvent.keyboard('cpu')

  button('cpunode').click()

  expect(clicks).toHaveBeenCalledTimes(1)
  expect(await state()).toBe('|-1|0')
  expect(button('cpunode')).toHaveFocus()
})

test('a click anywhere ends the search', async () => {
  render(fixture)
  await userEvent.keyboard('cpu')

  await fireEvent.pointerDown(document.body)

  expect(await state()).toBe('|-1|0')
  expect(document.body).toHaveFocus()
})

test('typing into a text field is typing, not searching', async () => {
  render(fixture)
  const input = screen.getByRole('textbox', { name: 'Search' })
  input.focus()

  await userEvent.keyboard('cpu')

  expect(input).toHaveValue('cpu')
  expect(await state()).toBe('|-1|0')
})

test('typing while the focus is outside the scope does nothing', async () => {
  render(fixture)
  button('cpu outside').focus()

  await userEvent.keyboard('cpu')

  expect(button('cpu outside')).toHaveFocus()
  expect(await state()).toBe('|-1|0')
})

test('a bound key does not start a search, but is typed once one is on', async () => {
  const unregister = registerKeyboardHelp([
    { kind: 'shortcut', scope: t('Table'), combo: ['/'], description: t('Focus search') }
  ])
  render(fixture)

  expect(claimed({ key: '/' })).toBe(false)
  expect(await state()).toBe('|-1|0')

  await userEvent.keyboard('cpu/')
  expect(await state()).toBe('cpu/|-1|0')
  unregister()
})

test('Space does not start a search, but is typed once one is on, without clicking', async () => {
  render(fixture)

  await userEvent.keyboard(' ')
  expect(await state()).toBe('|-1|0')

  await userEvent.keyboard('cpu ')
  expect(button('CPU load')).toHaveFocus()
  expect(await state()).toBe('cpu |0|1')
  expect(clicks).not.toHaveBeenCalled()
})

test('the page shortcuts are off while searching; the browser keys are not', async () => {
  const unregister = registerKeyboardHelp([
    { kind: 'shortcut', scope: t('Main menu'), combo: ['Alt', 'm'], description: t('Main menu') }
  ])
  render(fixture)
  expect(claimed({ key: 'm', altKey: true })).toBe(false)

  await userEvent.keyboard('cpu')

  expect(claimed({ key: 'm', altKey: true })).toBe(true)
  expect(claimed({ key: 'c', ctrlKey: true })).toBe(false)
  expect(claimed({ key: 'Enter' })).toBe(false)
  unregister()
})

test('the cheat sheet key still works while searching', async () => {
  const unregister = registerKeyboardHelp([
    { kind: 'shortcut', scope: t('Keyboard'), combo: ['Alt', 'k'], description: t('Cheat sheet') }
  ])
  render(fixture)

  await userEvent.keyboard('cpu')

  expect(claimed({ key: 'k', altKey: true })).toBe(false)
  unregister()
})

test('modifier combinations do not start a search', async () => {
  render(fixture)

  await userEvent.keyboard('{Alt>}c{/Alt}{Control>}p{/Control}')

  expect(await state()).toBe('|-1|0')
})

test('every match is marked while searching, and none once the search is over', async () => {
  render(fixture)

  await userEvent.keyboard('cpu')

  const marked = () => [...document.querySelectorAll(`[${MATCH_ATTRIBUTE}]`)]
  expect(marked()).toHaveLength(5)
  expect(marked()).toContain(document.activeElement)
  expect(button('dbnode')).not.toHaveAttribute(MATCH_ATTRIBUTE)

  await userEvent.keyboard('n')
  expect(marked()).toHaveLength(2)

  await userEvent.keyboard('{Escape}')
  expect(marked()).toHaveLength(0)
})
