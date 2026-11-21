/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import MapObjectActionBar from '@/maps/map/edit/components/MapObjectActionBar.vue'
import type { AnchorRect } from '@/maps/utils/anchorRect'

import { anObject } from '../../../support/fixtures'

// Embedded in the Checkmk page, the toolbar's fixed overlay is contained by the
// content area (left of it the navigation, right of it the sidebar) rather than
// the viewport. jsdom lays nothing out, so stand in for the browser's
// measurements.
const FRAME = { left: 74, top: 0, right: 874, bottom: 700 }
const BAR = { width: 200, height: 40 }

// What lies under a point of the screen, which jsdom does not know either.
let underPoint: (x: number, y: number) => Element[] = () => []

beforeEach(() => {
  underPoint = () => []
  Object.defineProperty(document, 'elementsFromPoint', {
    configurable: true,
    value: (x: number, y: number) => underPoint(x, y)
  })
})

function renderBar(anchor: AnchorRect) {
  return render(MapObjectActionBar, {
    props: {
      object: anObject({ id: 'h1', type: 'host', host_name: 'db01' }),
      anchor,
      selectedCount: 1,
      canBundle: false,
      isBundle: false
    }
  })
}

function measureInFrame(): void {
  const frame = document.createElement('div')
  frame.getBoundingClientRect = () =>
    ({ ...FRAME, width: FRAME.right - FRAME.left, height: FRAME.bottom - FRAME.top }) as DOMRect
  vi.spyOn(HTMLElement.prototype, 'offsetParent', 'get').mockReturnValue(frame)
  vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(BAR.width)
  vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(BAR.height)
}

async function renderAbove(anchor: AnchorRect): Promise<CSSStyleDeclaration> {
  measureInFrame()
  const { container } = renderBar(anchor)
  await nextTick()
  return container.querySelector<HTMLElement>('.maps-map-object-action-bar')!.style
}

describe('MapObjectActionBar placement', () => {
  it('sits centred above the object, in the frame coordinates rather than the viewport ones', async () => {
    const style = await renderAbove({ left: 300, right: 340, top: 200, bottom: 240 })

    // 320 (object centre) - 100 (half the bar) - 74 (frame left).
    expect(style.left).toBe('146px')
    // 200 (object top) - 8 (gap) - 40 (bar height).
    expect(style.top).toBe('152px')
  })

  it('sits below the object where there is no room above it', async () => {
    const style = await renderAbove({ left: 300, right: 340, top: 30, bottom: 70 })

    // 70 (object bottom) + 8 (gap).
    expect(style.top).toBe('78px')
  })

  it('sits below the object where above it would cover another one', async () => {
    const other = document.createElement('div')
    other.dataset['objectId'] = 'h2'
    underPoint = (_x, y) => (y < 200 ? [other] : [])

    const style = await renderAbove({ left: 300, right: 340, top: 200, bottom: 240 })

    // 240 (object bottom) + 8 (gap).
    expect(style.top).toBe('248px')
  })

  it('keeps its side while its object is dragged, and looks again once it rests', async () => {
    vi.useFakeTimers()
    const other = document.createElement('div')
    other.dataset['objectId'] = 'h2'
    const lookedAt: number[] = []
    underPoint = (_x, y) => {
      lookedAt.push(y)
      return y < 300 ? [other] : []
    }
    measureInFrame()
    const at = (top: number): AnchorRect => ({ left: 300, right: 340, top, bottom: top + 40 })
    const { container, rerender } = renderBar(at(400))
    await nextTick()
    const bar = container.querySelector<HTMLElement>('.maps-map-object-action-bar')!
    lookedAt.length = 0

    await rerender({ anchor: at(300) })
    await nextTick()
    expect(lookedAt).toEqual([])
    // 300 (object top) - 8 (gap) - 40 (bar height): above, as before the drag.
    expect(bar.style.top).toBe('252px')

    vi.advanceTimersByTime(150)
    await nextTick()
    // 340 (object bottom) + 8 (gap): above would now cover the other object.
    expect(bar.style.top).toBe('348px')
    vi.useRealTimers()
  })

  it('stays clear of the sidebar for an object at the right edge', async () => {
    const style = await renderAbove({ left: 850, right: 870, top: 200, bottom: 240 })

    // 874 (frame right) - 8 (margin) - 200 (bar width) - 74 (frame left).
    expect(style.left).toBe('592px')
  })

  it('is not shown while its object is panned out of the frame', async () => {
    // Left of the frame, where the navigation is.
    const style = await renderAbove({ left: 10, right: 50, top: 200, bottom: 240 })

    expect(style.visibility).toBe('hidden')
  })
})

describe('MapObjectActionBar', () => {
  it('asks for the properties when edit is clicked', async () => {
    const user = userEvent.setup()
    const { emitted } = renderBar({ left: 300, right: 340, top: 200, bottom: 240 })

    await user.click(await screen.findByRole('button', { name: 'Edit properties' }))

    expect(emitted('act')).toEqual([['edit']])
  })
})
