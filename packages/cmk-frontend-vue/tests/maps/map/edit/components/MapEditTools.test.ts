/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import { useMapEditor } from '@/maps/map/composables/useMapEditor'
import MapEditTools from '@/maps/map/edit/components/MapEditTools.vue'

import { aMap, anObject } from '../../../support/fixtures'
import { fakeMapsServices, mapsGlobal, runWithServices } from '../../../support/services'

/** The tools in edit mode over a map with two objects on it. */
function renderTools(selection: string[], keyboardActive = true) {
  const services = fakeMapsServices()
  const map = aMap({
    objects: [
      anObject({ id: 'host1', type: 'host', x: 10, y: 10 }),
      anObject({ id: 'host2', type: 'host', x: 40, y: 10 })
    ]
  })
  services.maps.currentMap.value = map
  const editor = runWithServices(services, () => useMapEditor())
  editor.toggleEditMode()
  editor.selectObjects(selection)

  const rendered = render(MapEditTools, {
    props: {
      editor,
      connectionId: 'test',
      offersAddObject: true,
      offersGrid: true,
      keyboardActive
    },
    global: mapsGlobal({}, services)
  })
  return { ...rendered, map, editor }
}

describe('MapEditTools – keyboard shortcuts', () => {
  // Deleting is confirmed and takes the whole selection, both of which live in
  // the view. The keys must therefore ask, not reach into the editor.
  it('hands Delete to the view instead of removing the object itself', async () => {
    const { emitted, map } = renderTools(['host1'])

    await userEvent.keyboard('{Delete}')

    expect(emitted()['delete-selection']).toHaveLength(1)
    expect(map.objects.map((o) => o.id)).toEqual(['host1', 'host2'])
  })

  it('hands Delete to the view for a multi-selection too', async () => {
    const { emitted, map } = renderTools(['host1', 'host2'])

    await userEvent.keyboard('{Delete}')

    expect(emitted()['delete-selection']).toHaveLength(1)
    expect(map.objects).toHaveLength(2)
  })

  it('duplicates a single object on Ctrl+D', async () => {
    const { emitted } = renderTools(['host1'])

    await userEvent.keyboard('{Control>}d{/Control}')

    expect(emitted()['duplicate-selection']).toHaveLength(1)
  })

  // Duplicate is offered for one object only, so the key that stands for it
  // must not quietly pick one out of several.
  it('stays quiet on Ctrl+D while several objects are selected', async () => {
    const { emitted } = renderTools(['host1', 'host2'])

    await userEvent.keyboard('{Control>}d{/Control}')

    expect(emitted()['duplicate-selection']).toBeUndefined()
  })

  // A dialog over the map owns the keyboard: Backspace typed into the settings
  // slide-in belongs to the field it was typed in, not to the object behind it.
  it('lets go of the keyboard while a dialog is open', async () => {
    const { emitted } = renderTools(['host1'], false)

    await userEvent.keyboard('{Delete}')
    await userEvent.keyboard('{Control>}d{/Control}')

    expect(emitted()['delete-selection']).toBeUndefined()
    expect(emitted()['duplicate-selection']).toBeUndefined()
  })
})

describe('MapEditTools – the add-object panel', () => {
  it('opens and closes the panel from its button', async () => {
    renderTools([])
    const button = screen.getByRole('button', { name: 'Add object' })

    await userEvent.click(button)
    expect(await screen.findByRole('combobox', { name: 'Object type' })).toBeInTheDocument()

    await userEvent.click(button)
    await waitFor(() =>
      expect(screen.queryByRole('combobox', { name: 'Object type' })).not.toBeInTheDocument()
    )
  })

  // The type is picked in the panel and nowhere else, so the button opens a
  // form rather than a menu listing the same types a second time.
  it('offers no separate type menu', async () => {
    renderTools([])

    await userEvent.click(screen.getByRole('button', { name: 'Add object' }))

    await screen.findByRole('combobox', { name: 'Object type' })
    expect(screen.queryByRole('menu', { name: 'Select type…' })).not.toBeInTheDocument()
  })

  // The panel sits in the corner of the canvas: left open while placing, it
  // would swallow the click meant for the map underneath it.
  it('shrinks to its header while placing, freeing the canvas beneath it', async () => {
    const { editor } = renderTools([])

    await userEvent.click(screen.getByRole('button', { name: 'Add object' }))
    await screen.findByRole('combobox', { name: 'Object type' })

    editor.placing.value = true

    await waitFor(() =>
      expect(screen.queryByRole('combobox', { name: 'Object type' })).not.toBeInTheDocument()
    )
    expect(screen.getByText('Click on map to place…')).toBeInTheDocument()
  })
})

describe('MapEditTools – reaching the grid menu by keyboard', () => {
  it('puts the menu after its button, so Tab walks into it', async () => {
    renderTools([])
    const button = screen.getByRole('button', { name: 'Grid' })

    await userEvent.click(button)

    const menu = await screen.findByRole('menu', { name: 'Grid' })
    expect(button.compareDocumentPosition(menu) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('moves the focus into the menu on open and back to the button on Escape', async () => {
    renderTools([])
    const button = screen.getByRole('button', { name: 'Grid' })

    await userEvent.click(button)
    const items = await screen.findAllByRole('menuitemradio')
    await waitFor(() => expect(items[0]).toHaveFocus())

    await userEvent.keyboard('{ArrowDown}')
    expect(items[1]).toHaveFocus()

    await userEvent.keyboard('{Escape}')
    await waitFor(() => expect(button).toHaveFocus())
  })
})
