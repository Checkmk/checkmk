/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, test, vi } from 'vitest'
import { nextTick, ref } from 'vue'

import { useSegmentFocus } from '@/components/date-time/private/input/useSegmentFocus'

const SEGMENT_ORDER = ['day', 'month', 'year']

const stubInput = (): HTMLInputElement => {
  const el = document.createElement('input')
  vi.spyOn(el, 'focus')
  vi.spyOn(el, 'select')
  return el
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useSegmentFocus', () => {
  test('registerInput stores element', async () => {
    const focus = useSegmentFocus(() => SEGMENT_ORDER, vi.fn())
    const day = stubInput()
    focus.registerInput('day', day)
    focus.focusFirst()
    await nextTick()
    expect(day.focus).toHaveBeenCalled()
    expect(day.select).toHaveBeenCalled()
  })

  test('moveFocus to next neighbor', async () => {
    const focus = useSegmentFocus(() => SEGMENT_ORDER, vi.fn())
    const month = stubInput()
    focus.registerInput('month', month)
    focus.moveFocus('day', 1)
    await nextTick()
    expect(month.focus).toHaveBeenCalled()
  })

  test('moveFocus to previous neighbor', async () => {
    const focus = useSegmentFocus(() => SEGMENT_ORDER, vi.fn())
    const day = stubInput()
    focus.registerInput('day', day)
    focus.moveFocus('month', -1)
    await nextTick()
    expect(day.focus).toHaveBeenCalled()
  })

  test('moveFocus past last → navigateOut', async () => {
    const navigateOut = vi.fn()
    const focus = useSegmentFocus(() => SEGMENT_ORDER, navigateOut)
    const year = stubInput()
    focus.registerInput('year', year)
    focus.moveFocus('year', 1)
    await nextTick()
    expect(navigateOut).toHaveBeenCalledWith(1)
    expect(year.focus).not.toHaveBeenCalled()
  })

  test('moveFocus past first → navigateOut', async () => {
    const navigateOut = vi.fn()
    const focus = useSegmentFocus(() => SEGMENT_ORDER, navigateOut)
    focus.moveFocus('day', -1)
    await nextTick()
    expect(navigateOut).toHaveBeenCalledWith(-1)
  })

  test('focusFirst', async () => {
    const focus = useSegmentFocus(() => SEGMENT_ORDER, vi.fn())
    const day = stubInput()
    focus.registerInput('day', day)
    focus.focusFirst()
    await nextTick()
    expect(day.focus).toHaveBeenCalled()
  })

  test('focusLast', async () => {
    const focus = useSegmentFocus(() => SEGMENT_ORDER, vi.fn())
    const year = stubInput()
    focus.registerInput('year', year)
    focus.focusLast()
    await nextTick()
    expect(year.focus).toHaveBeenCalled()
  })

  test('reactive reorder honored', async () => {
    const order = ref([...SEGMENT_ORDER])
    const focus = useSegmentFocus(() => order.value, vi.fn())
    const month = stubInput()
    focus.registerInput('month', month)
    order.value = ['month', 'day', 'year']
    focus.focusFirst()
    await nextTick()
    expect(month.focus).toHaveBeenCalled()
  })

  test('unknown / unregistered key is a no-op', async () => {
    const focus = useSegmentFocus(() => SEGMENT_ORDER, vi.fn())
    expect(() => {
      focus.focusFirst()
      focus.moveFocus('day', 1)
    }).not.toThrow()
    await nextTick()
  })
})
