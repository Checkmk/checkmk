/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest'

import { useDragReorder } from '@/maps/shared/composables/useDragReorder'

function dragEvent(dropEffect: 'none' | 'move' = 'none'): DragEvent {
  const target = document.createElement('div')
  return {
    dataTransfer: {
      dropEffect,
      effectAllowed: 'uninitialized',
      setData: vi.fn(),
      setDragImage: vi.fn()
    },
    currentTarget: target,
    clientX: 0,
    clientY: 0,
    preventDefault: vi.fn()
  } as unknown as DragEvent
}

function setup(initial: string[] = ['a', 'b', 'c', 'd'], enabled = true) {
  let list = [...initial]
  const onFinished = vi.fn()
  const api = useDragReorder<string>(
    () => list,
    (next) => {
      list = next
    },
    onFinished,
    () => enabled
  )
  return { api, onFinished, getList: () => list }
}

describe('useDragReorder', () => {
  it('reorders live on dragover and persists on completed drop (dropEffect move)', () => {
    const { api, onFinished, getList } = setup()
    api.onDragStart(dragEvent(), 0)
    api.onDragOver(dragEvent(), 2)
    expect(getList()).toEqual(['b', 'c', 'a', 'd'])
    api.onDragEnd(dragEvent('move'))
    expect(onFinished).toHaveBeenCalledTimes(1)
    expect(getList()).toEqual(['b', 'c', 'a', 'd'])
  })

  it('reverts to the original order on cancelled drag (dropEffect none)', () => {
    const { api, onFinished, getList } = setup()
    api.onDragStart(dragEvent(), 0)
    api.onDragOver(dragEvent(), 3)
    expect(getList()).toEqual(['b', 'c', 'd', 'a'])
    api.onDragEnd(dragEvent('none'))
    expect(onFinished).not.toHaveBeenCalled()
    expect(getList()).toEqual(['a', 'b', 'c', 'd'])
  })

  it('does nothing while disabled — bubbled dragstart from draggable children', () => {
    const { api, onFinished, getList } = setup(['a', 'b', 'c'], false)
    api.onDragStart(dragEvent(), 0)
    api.onDragOver(dragEvent(), 2)
    api.onDragEnd(dragEvent('move'))
    expect(getList()).toEqual(['a', 'b', 'c'])
    expect(onFinished).not.toHaveBeenCalled()
  })

  it('ignores dragover from external drags (no own dragstart)', () => {
    const { api, getList } = setup()
    const ev = dragEvent()
    api.onDragOver(ev, 1)
    expect(getList()).toEqual(['a', 'b', 'c', 'd'])
    expect(ev.preventDefault).not.toHaveBeenCalled()
  })

  it('does not persist a no-movement drag end without prior dragstart', () => {
    const { api, onFinished } = setup()
    api.onDragEnd(dragEvent('move'))
    expect(onFinished).not.toHaveBeenCalled()
  })
})
