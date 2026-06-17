/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, test, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import { useListboxColumn } from '@/components/date-time/private/time-selector/useListboxColumn'

const keyEvent = (key: string): KeyboardEvent =>
  ({ key, preventDefault: vi.fn() }) as unknown as KeyboardEvent

const setup = (selectedValue: number) => {
  const selected: Ref<number> = ref(selectedValue)
  const navigate = vi.fn()
  const commit = vi.fn()
  const scroller = ref<HTMLElement | null>(null)
  const listbox = ref<HTMLDivElement | null>(null)
  const column = useListboxColumn<number>({
    options: () => [1, 2, 3],
    selected,
    scroller: () => scroller.value,
    listbox: () => listbox.value,
    navigate,
    commit
  })
  return { selected, navigate, commit, scroller, listbox, column }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useListboxColumn — keyboard', () => {
  test.each([
    { key: 'ArrowDown', initial: 2, expected: 3, label: 'ArrowDown next' },
    { key: 'ArrowDown', initial: 3, expected: 1, label: 'ArrowDown wraps' },
    { key: 'ArrowUp', initial: 1, expected: 3, label: 'ArrowUp wraps' },
    {
      key: 'ArrowDown',
      initial: 99,
      expected: 1,
      label: 'selection not in options (ArrowDown) → first'
    },
    {
      key: 'ArrowUp',
      initial: 99,
      expected: 3,
      label: 'selection not in options (ArrowUp) → last'
    }
  ])('$label', ({ initial, expected, key }) => {
    const { selected, column } = setup(initial)
    column.onKeydown(keyEvent(key))
    expect(selected.value).toBe(expected)
  })

  test.each([
    { key: 'ArrowLeft', expected: 'previous' as const },
    { key: 'ArrowRight', expected: 'next' as const }
  ])('$key navigates $expected', ({ key, expected }) => {
    const { navigate, column } = setup(2)
    const event = keyEvent(key)
    column.onKeydown(event)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith(expected)
  })

  test('Enter commits', () => {
    const { commit, column } = setup(2)
    const event = keyEvent('Enter')
    column.onKeydown(event)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(commit).toHaveBeenCalled()
  })

  test('other key ignored', () => {
    const { navigate, commit, column } = setup(2)
    const event = keyEvent('Tab')
    column.onKeydown(event)
    expect(event.preventDefault).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
    expect(commit).not.toHaveBeenCalled()
  })
})

describe('useListboxColumn — focus & centering', () => {
  test('focusSelected focuses selected button', async () => {
    const { listbox, column } = setup(2)
    const box = document.createElement('div')
    const button = document.createElement('button')
    button.setAttribute('aria-selected', 'true')
    box.appendChild(button)
    listbox.value = box
    const focus = vi.spyOn(button, 'focus')
    column.focusSelected()
    await nextTick()
    expect(focus).toHaveBeenCalled()
  })

  test('focusSelected no selection', async () => {
    const { listbox, column } = setup(2)
    const box = document.createElement('div')
    box.appendChild(document.createElement('button'))
    listbox.value = box
    expect(() => column.focusSelected()).not.toThrow()
    await nextTick()
  })

  test('centerSelected math (stubbed rects)', () => {
    const { scroller, listbox, column } = setup(2)
    const scrollerEl = document.createElement('div')
    Object.defineProperty(scrollerEl, 'clientHeight', { value: 200, configurable: true })
    scrollerEl.scrollTop = 0
    vi.spyOn(scrollerEl, 'getBoundingClientRect').mockReturnValue({
      top: 0,
      bottom: 0,
      left: 0,
      right: 0,
      width: 0,
      height: 0,
      x: 0,
      y: 0
    } as DOMRect)

    const box = document.createElement('div')
    const button = document.createElement('button')
    button.setAttribute('aria-selected', 'true')
    box.appendChild(button)
    Object.defineProperty(button, 'offsetHeight', { value: 20, configurable: true })
    vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({
      top: 100,
      bottom: 100,
      left: 0,
      right: 0,
      width: 0,
      height: 0,
      x: 0,
      y: 0
    } as DOMRect)

    scroller.value = scrollerEl
    listbox.value = box
    column.centerSelected()
    expect(scrollerEl.scrollTop).toBe(10)
  })

  test('centerSelected null refs', () => {
    const { column } = setup(2)
    expect(() => column.centerSelected()).not.toThrow()
  })
})
