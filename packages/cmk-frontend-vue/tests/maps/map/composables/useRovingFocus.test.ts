/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import { useRovingFocus } from '@/maps/map/composables/useRovingFocus'
import type { MapElement, ObjectState } from '@/maps/types/api'

import { aState, anObject } from '../../support/fixtures'

const objects: MapElement[] = [
  anObject({ id: 'b', type: 'host', host_name: 'bravo' }),
  anObject({ id: 'a', type: 'host', host_name: 'alpha' }),
  anObject({ id: 'd', type: 'host', host_name: 'delta' })
]

const states: Record<string, ObjectState> = {
  a: aState({ object_id: 'a', type: 'host', state: 'UP' }),
  b: aState({ object_id: 'b', type: 'host', state: 'UP' }),
  d: aState({ object_id: 'd', type: 'host', state: 'DOWN' })
}

/** A map of three focusable objects, with a control before it. */
function renderMap(reveal = vi.fn()) {
  render(
    defineComponent({
      setup() {
        const root = ref<HTMLElement | null>(null)
        const roving = useRovingFocus({
          objects: () => objects,
          states: () => states,
          nameOf: (object) => object.host_name ?? '',
          root: () => root.value,
          reveal
        })
        return { root, roving, objects }
      },
      template: `
        <button>Search</button>
        <div ref="root" @keydown="roving.onKeydown" @focusin="roving.onFocusin">
          <div
            v-for="object in objects"
            :key="object.id"
            :data-object-id="object.id"
            :tabindex="roving.isTabStop(object.id) ? 0 : -1"
            role="button"
            :aria-label="object.host_name"
          />
        </div>
        <button>Edit</button>`
    })
  )
  return reveal
}

describe('useRovingFocus', () => {
  it('makes the whole map one tab stop, on the worst state first', async () => {
    const user = userEvent.setup()
    renderMap()

    await user.tab()
    await user.tab()
    expect(screen.getByRole('button', { name: 'delta' })).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: 'Edit' })).toHaveFocus()
  })

  it('brings the object tabbed to into view instead of scrolling to it', async () => {
    const user = userEvent.setup()
    const reveal = renderMap()

    await user.tab()
    await user.tab()

    expect(reveal).toHaveBeenLastCalledWith(objects[2])
    const focus = vi.spyOn(HTMLElement.prototype, 'focus')
    await user.keyboard('{ArrowRight}')
    expect(focus).toHaveBeenLastCalledWith({ preventScroll: true })
    focus.mockRestore()
  })

  it('moves between the objects with the arrow keys, worst first, then by name', async () => {
    const user = userEvent.setup()
    const reveal = renderMap()
    screen.getByRole('button', { name: 'delta' }).focus()

    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('button', { name: 'alpha' })).toHaveFocus()
    expect(reveal).toHaveBeenLastCalledWith(objects[1])

    await user.keyboard('{End}')
    expect(screen.getByRole('button', { name: 'bravo' })).toHaveFocus()

    await user.keyboard('{Home}')
    expect(screen.getByRole('button', { name: 'delta' })).toHaveFocus()
  })

  it('keeps the tab stop on the object focused last', async () => {
    const user = userEvent.setup()
    renderMap()

    await user.click(screen.getByRole('button', { name: 'bravo' }))

    expect(screen.getByRole('button', { name: 'bravo' })).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('button', { name: 'delta' })).toHaveAttribute('tabindex', '-1')
  })
})
