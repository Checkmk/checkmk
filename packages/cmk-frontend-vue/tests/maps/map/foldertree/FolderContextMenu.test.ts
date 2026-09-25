/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import FolderContextMenu from '@/maps/map/foldertree/components/FolderContextMenu.vue'

import { aFolderNode } from '../../support/fixtures'

/**
 * A right-click opens the menu and leaves the focus where it was, so the case
 * mounts it the way the map view does -- open, with nothing inside it focused --
 * and closes it by taking the menu away.
 */
const hostComponent = defineComponent({
  components: { FolderContextMenu },
  setup() {
    const open = ref(true)
    const folder = aFolderNode({
      path: '/main/web',
      title: 'Web servers',
      kind: 'folder',
      host_count: 3
    })
    return { open, folder }
  },
  template: `<FolderContextMenu
    v-if="open"
    :folder="folder"
    :x="10"
    :y="10"
    checkmk-url="http://checkmk/site"
    :can-command="true"
    @close="open = false"
  />`
})

describe('FolderContextMenu', () => {
  it('closes on Escape without the operator having to tab into it first', async () => {
    const user = userEvent.setup()
    render(hostComponent)
    // Measured invisibly first, then shown where it opens.
    expect(await screen.findByRole('button', { name: /Folder actions/ })).toBeInTheDocument()

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('button', { name: /Folder actions/ })).toBeNull()
  })
})

describe('FolderContextMenu placement', () => {
  // Embedded in the Checkmk page, the menu's fixed overlay is contained by the
  // content area (left of it the navigation, right of it the sidebar) rather
  // than the viewport. jsdom lays nothing out, so stand in for the browser's
  // measurements.
  const FRAME = { left: 74, top: 0, right: 874, bottom: 700 }
  const MENU = { width: 224, height: 120 }

  async function renderAt(x: number, y: number): Promise<CSSStyleDeclaration> {
    const frame = document.createElement('div')
    frame.getBoundingClientRect = () =>
      ({ ...FRAME, width: FRAME.right - FRAME.left, height: FRAME.bottom - FRAME.top }) as DOMRect
    vi.spyOn(HTMLElement.prototype, 'offsetParent', 'get').mockReturnValue(frame)
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(MENU.width)
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(MENU.height)
    const { container } = render(FolderContextMenu, {
      props: {
        folder: aFolderNode({ path: '/main/web', title: 'Web servers', kind: 'folder' }),
        x,
        y,
        checkmkUrl: 'http://checkmk/site',
        canCommand: true
      }
    })
    const menu = container.querySelector<HTMLElement>('.maps-folder-context-menu')!
    // Measured invisibly first; the placement lands once the menu is in the DOM.
    await waitFor(() => expect(menu.style.visibility).not.toBe('hidden'))
    return menu.style
  }

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens at the pointer, in the frame coordinates rather than the viewport ones', async () => {
    const style = await renderAt(300, 200)

    // 300 (pointer, viewport) - 74 (frame left).
    expect(style.left).toBe('226px')
    expect(style.top).toBe('200px')
  })

  it('opens left of the pointer where it would run under the sidebar', async () => {
    const style = await renderAt(700, 200)

    // 700 (pointer) - 224 (menu width) - 74 (frame left).
    expect(style.left).toBe('402px')
  })

  it('opens above the pointer where it would run past the bottom', async () => {
    const style = await renderAt(300, 650)

    // 650 (pointer) - 120 (menu height).
    expect(style.top).toBe('530px')
  })

  it('moves above the pointer once it grows past the bottom while open', async () => {
    // jsdom has no layout, so a resize is announced by hand.
    const resizes: (() => void)[] = []
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(onResize: ResizeObserverCallback) {
          resizes.push(() => onResize([], this as unknown as ResizeObserver))
        }
        observe(): void {}
        unobserve(): void {}
        disconnect(): void {}
      }
    )
    const style = await renderAt(300, 500)
    expect(style.top).toBe('500px')

    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(250)
    resizes.forEach((resize) => resize())

    // 500 (pointer) - 250 (grown menu height).
    await waitFor(() => expect(style.top).toBe('250px'))
    vi.unstubAllGlobals()
  })
})
