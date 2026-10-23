/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, reactive } from 'vue'

import PresentationInspectorPanel from '@/maps/map/presentation/components/PresentationInspectorPanel.vue'
import { createElement } from '@/maps/map/presentation/elements'
import type { PresentationElement, PresentationView } from '@/maps/types/api'

import { newMapView } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

const { mockConnectionsApi } = vi.hoisted(() => ({
  mockConnectionsApi: {
    objects: vi.fn().mockResolvedValue([]),
    perfMetrics: vi.fn().mockResolvedValue([]),
    list: vi.fn().mockResolvedValue([])
  }
}))

function makeView(): PresentationView {
  return { ...newMapView('presentation'), elements: [] } as PresentationView
}

// The panel's contract towards the editor is its emits; capture them through
// real handlers on a host wrapper instead of inspecting emitted events.
interface CapturedEvents {
  slide: Record<string, unknown> | null
  patches: Record<string, unknown>[]
  group: number
  save: number
}

function renderPanel(selection: PresentationElement[]): CapturedEvents {
  const captured = reactive<CapturedEvents>({ slide: null, patches: [], group: 0, save: 0 })
  render(
    defineComponent({
      components: { PresentationInspectorPanel },
      setup() {
        return {
          selection,
          view: makeView(),
          onSlide: (payload: Record<string, unknown>) => {
            captured.slide = payload
          },
          onPatch: (payload: Record<string, unknown>) => {
            captured.patches.push(payload)
          },
          onGroup: () => {
            captured.group += 1
          },
          onSave: () => {
            captured.save += 1
          }
        }
      },
      template: `
        <PresentationInspectorPanel
          :selection="selection"
          :view="view"
          connection-id="live_1"
          :targets="[]"
          background-image-name=""
          save-label=""
          @slide="onSlide"
          @patch="onPatch"
          @group="onGroup"
          @save="onSave"
        />
      `
    }),
    { global: mapsGlobal() }
  )
  return captured
}

describe('PresentationInspectorPanel', () => {
  beforeEach(() => {
    mockConnectionsApi.objects.mockClear()
    // The binding form's autocomplete teleports its dropdown to #app (the SPA
    // root); give the teleport a real target so it renders into the document.
    const app = document.createElement('div')
    app.id = 'app'
    document.body.appendChild(app)
  })

  afterEach(() => {
    document.getElementById('app')?.remove()
  })

  it('shows slide settings when nothing is selected', () => {
    renderPanel([])
    expect(screen.getByRole('button', { name: 'Slide' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Aspect / size' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Background' })).toBeInTheDocument()
  })

  it('reports a slide change for a size preset', async () => {
    const user = userEvent.setup()
    const captured = renderPanel([])
    await user.click(screen.getByRole('button', { name: '16:9' }))
    expect(captured.slide).toEqual({ width: 1920, height: 1080 })
  })

  it('shows layout + typography for a text element and reports patches', async () => {
    const user = userEvent.setup()
    const text = createElement('text', 0, 0)
    const captured = renderPanel([text])
    expect(screen.getByRole('heading', { name: 'Layout' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Typography' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'B' }))
    expect(captured.patches[0]).toHaveProperty('font_weight')
  })

  // Vue's number cast hands back the raw string for a cleared type="number"
  // field, so an unguarded patch would write "" and the server would then
  // reject every later save of the map.
  it('patches nothing when a numeric field is cleared', async () => {
    const user = userEvent.setup()
    const text = createElement('text', 0, 0)
    const captured = renderPanel([text])

    await user.clear(screen.getByRole('spinbutton', { name: 'X' }))
    expect(captured.patches).toEqual([])
  })

  it('reports the slide size only once the field settles', async () => {
    const user = userEvent.setup()
    const captured = renderPanel([])
    const width = screen.getByRole('spinbutton', { name: 'Width' })

    await user.clear(width)
    await user.type(width, '2560')
    expect(captured.slide).toBeNull()

    await user.tab()
    expect(captured.slide).toEqual({ width: 2560 })
  })

  it('shows appearance + data sections for a shape', () => {
    const shape = createElement('rect', 0, 0)
    renderPanel([shape])
    expect(screen.getByRole('heading', { name: 'Appearance' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Data' })).toBeInTheDocument()
    expect(screen.getByText(/Data slot/)).toBeInTheDocument()
  })

  it('shows display controls and binding form for a data element', () => {
    const data = createElement('data', 0, 0)
    renderPanel([data])
    expect(screen.getByRole('heading', { name: 'Layout' })).toBeInTheDocument()
    expect(screen.getByText('Host')).toBeInTheDocument()
    expect(screen.getByText('Display')).toBeInTheDocument()
  })

  it('hides the layout numbers for connectors', () => {
    const line = createElement('line', 0, 0)
    renderPanel([line])
    expect(screen.queryByRole('heading', { name: 'Layout' })).toBeNull()
    expect(screen.getByText('Start endpoint')).toBeInTheDocument()
  })

  it('shows the shared subset for a multi-selection', () => {
    const a = createElement('rect', 0, 0)
    const b = createElement('text', 0, 0)
    renderPanel([a, b])
    expect(screen.getByText('2 elements selected')).toBeInTheDocument()
    // The shared opacity control is the range slider.
    expect(screen.getByRole('slider')).toBeInTheDocument()
  })

  it('reports group/ungroup from the multi-selection actions', async () => {
    const user = userEvent.setup()
    const a = createElement('rect', 0, 0)
    const b = createElement('text', 0, 0)
    const captured = renderPanel([a, b])

    await user.click(screen.getByRole('button', { name: 'Group' }))
    expect(captured.group).toBe(1)
    expect(screen.getByRole('button', { name: 'Ungroup' })).toBeDisabled()
  })

  it('switches between Slide and Element context via the top bar tabs', async () => {
    const user = userEvent.setup()
    const shape = createElement('rect', 0, 0)
    renderPanel([shape])
    expect(screen.getByRole('heading', { name: 'Appearance' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Slide' }))
    expect(screen.getByRole('heading', { name: 'Aspect / size' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Element' }))
    expect(screen.getByRole('heading', { name: 'Appearance' })).toBeInTheDocument()
  })

  it('reports save from the topbar save button', async () => {
    const user = userEvent.setup()
    const captured = renderPanel([])
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(captured.save).toBe(1)
  })

  it('renames the element via the header input', async () => {
    const user = userEvent.setup()
    const shape = createElement('rect', 0, 0)
    const captured = renderPanel([shape])

    const name = screen.getByRole('textbox', { name: 'Element name' })
    await user.clear(name)
    await user.type(name, 'Core switch')
    // The rename patch is emitted on change, i.e. when the input loses focus.
    await user.tab()

    expect(captured.patches[captured.patches.length - 1]).toEqual({ name: 'Core switch' })
  })
})
