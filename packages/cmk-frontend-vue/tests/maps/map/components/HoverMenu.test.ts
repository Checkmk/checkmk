/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, waitFor } from '@testing-library/vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import HoverMenu from '@/maps/map/components/HoverMenu.vue'
import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'

import { anObject } from '../../support/fixtures'
import { mapsGlobal } from '../../support/services'

// Embedded in the Checkmk page, the card's fixed overlay is contained by the
// content area (left of it the navigation, right of it the sidebar) rather than
// the viewport. jsdom lays nothing out and has a 1024px wide window, so stand in
// for the browser's measurements.
const FRAME = { left: 74, top: 0, width: 800, height: 700 }
const CARD = { width: 288, height: 160 }

function measureAs(frame: typeof FRAME, card: typeof CARD): void {
  const parent = document.createElement('div')
  parent.getBoundingClientRect = () =>
    ({ ...frame, right: frame.left + frame.width, bottom: frame.top + frame.height }) as DOMRect
  vi.spyOn(HTMLElement.prototype, 'offsetParent', 'get').mockReturnValue(parent)
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    ...card,
    left: 0,
    top: 0,
    right: card.width,
    bottom: card.height
  } as DOMRect)
}

async function renderPlaced(
  x: number,
  y: number,
  anchorRect: HoverAnchorRect | null
): Promise<CSSStyleDeclaration> {
  measureAs(FRAME, CARD)
  const { container } = render(HoverMenu, {
    props: {
      object: anObject({ id: 'o1', type: 'host', host_name: 'web01' }),
      state: undefined,
      x,
      y,
      anchorRect
    },
    global: mapsGlobal()
  })
  const root = container.querySelector<HTMLElement>('.maps-hover-menu')!
  // Measured invisibly first; the placement lands once the card is in the DOM.
  await waitFor(() => expect(root.style.visibility).not.toBe('hidden'))
  return root.style
}

describe('HoverMenu placement', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens at the pointer, in the frame coordinates rather than the viewport ones', async () => {
    const style = await renderPlaced(300, 200, { left: 270, top: 180, right: 310, bottom: 230 })

    // 300 (pointer, viewport) - 74 (frame left).
    expect(style.left).toBe('226px')
    expect(style.top).toBe('200px')
  })

  it('flips left of the object where the card would run under the sidebar', async () => {
    // The window still has room right of the pointer; the frame, which ends
    // where the sidebar begins, does not.
    const style = await renderPlaced(602, 200, { left: 570, top: 180, right: 610, bottom: 230 })

    // 570 (anchor left) - 288 (card width) - 8 (gap) - 74 (frame left).
    expect(style.left).toBe('200px')
  })
})
