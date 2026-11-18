/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import MapsMenu from '@/maps/shared/components/MapsMenu.vue'
import MapsMenuItem from '@/maps/shared/components/MapsMenuItem.vue'

/** Opened the way the map views do it: mounted at the pointer, taken away on close. */
function renderMenu(opened = true) {
  const open = ref(opened)
  const at = ref({ x: 10, y: 10 })
  const picked = ref<string[]>([])
  render(
    defineComponent({
      components: { MapsMenu, MapsMenuItem },
      setup: () => ({ open, at, picked }),
      template: `
        <button type="button">Opener</button>
        <button type="button">Elsewhere</button>
        <MapsMenu v-if="open" :x="at.x" :y="at.y" label="web01" heading="web01" @close="open = false">
          <MapsMenuItem href="http://checkmk/site/host">Host in Checkmk</MapsMenuItem>
          <MapsMenuItem @click="picked.push('edit')">Edit</MapsMenuItem>
          <MapsMenuItem danger @click="picked.push('delete')">Delete</MapsMenuItem>
        </MapsMenu>`
    })
  )
  return { open, at, picked }
}

function entry(name: string): HTMLElement {
  return screen.getByRole('menuitem', { name })
}

describe('MapsMenu', () => {
  it('moves the focus to its first entry when it opens', async () => {
    renderMenu()

    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())
  })

  it('takes the focus only once it is shown', async () => {
    // A browser refuses the focus to an invisible element, and the menu is
    // measured invisibly before it is placed; jsdom would not refuse it.
    const shownWhenFocused: boolean[] = []
    vi.spyOn(HTMLElement.prototype, 'focus').mockImplementation(function (this: HTMLElement) {
      shownWhenFocused.push(
        this.closest<HTMLElement>('[role="menu"]')?.style.visibility !== 'hidden'
      )
    })
    renderMenu()

    await waitFor(() => expect(shownWhenFocused).toEqual([true]))
  })

  it('walks its entries with the arrow keys, round at either end', async () => {
    const user = userEvent.setup()
    renderMenu()
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())

    await user.keyboard('{ArrowDown}')
    expect(entry('Edit')).toHaveFocus()
    await user.keyboard('{ArrowUp}{ArrowUp}')
    expect(entry('Delete')).toHaveFocus()
    await user.keyboard('{Home}')
    expect(entry('Host in Checkmk')).toHaveFocus()
    await user.keyboard('{End}')
    expect(entry('Delete')).toHaveFocus()
  })

  it('runs an entry and closes on Escape', async () => {
    const user = userEvent.setup()
    const { open, picked } = renderMenu()
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())

    await user.keyboard('{ArrowDown}{Enter}')
    expect(picked.value).toEqual(['edit'])

    await user.keyboard('{Escape}')
    expect(open.value).toBe(false)
  })

  it('closes on a click outside it', async () => {
    const user = userEvent.setup()
    const { open } = renderMenu()
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())

    await user.click(screen.getByRole('button', { name: 'Elsewhere' }))

    expect(open.value).toBe(false)
  })

  it('puts the focus back where it was once closed', async () => {
    const user = userEvent.setup()
    const { open } = renderMenu(false)
    screen.getByRole('button', { name: 'Opener' }).focus()
    open.value = true
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())

    await user.keyboard('{Escape}')

    await waitFor(() => expect(screen.getByRole('button', { name: 'Opener' })).toHaveFocus())
  })

  it('puts the focus back where the last right-click was, when it opens again elsewhere', async () => {
    const user = userEvent.setup()
    const { open, at } = renderMenu(false)
    screen.getByRole('button', { name: 'Opener' }).focus()
    open.value = true
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())

    // A right-click focuses what it hits, and fires no click to close the menu.
    screen.getByRole('button', { name: 'Elsewhere' }).focus()
    at.value = { x: 50, y: 50 }
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())
    await user.keyboard('{Escape}')

    await waitFor(() => expect(screen.getByRole('button', { name: 'Elsewhere' })).toHaveFocus())
  })

  it('puts the focus back before an entry acts, for a dialog the entry opens', async () => {
    const user = userEvent.setup()
    const { open } = renderMenu(false)
    const opener = screen.getByRole('button', { name: 'Opener' })
    opener.focus()
    open.value = true
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())
    let focusedWhenActing: Element | null = null
    entry('Edit').addEventListener('click', () => (focusedWhenActing = document.activeElement))

    await user.click(entry('Edit'))

    expect(focusedWhenActing).toBe(opener)
  })

  it('leaves the focus where a click outside it put it', async () => {
    const user = userEvent.setup()
    const { open } = renderMenu(false)
    screen.getByRole('button', { name: 'Opener' }).focus()
    open.value = true
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())

    await user.click(screen.getByRole('button', { name: 'Elsewhere' }))

    await waitFor(() => expect(open.value).toBe(false))
    expect(screen.getByRole('button', { name: 'Elsewhere' })).toHaveFocus()
  })

  it('stays open on a click inside it', async () => {
    const user = userEvent.setup()
    const { open } = renderMenu()
    await waitFor(() => expect(entry('Host in Checkmk')).toHaveFocus())

    await user.click(screen.getByText('web01'))

    expect(open.value).toBe(true)
  })

  it('opens a link entry in a new tab', async () => {
    renderMenu()

    expect(await screen.findByRole('menuitem', { name: 'Host in Checkmk' })).toHaveAttribute(
      'target',
      '_blank'
    )
    expect(entry('Host in Checkmk')).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
