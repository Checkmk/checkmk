/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import PresentationCanvas from '@/maps/map/presentation/components/PresentationCanvas.vue'
import { createElement } from '@/maps/map/presentation/elements'
import type {
  DataElement,
  MapConfig,
  MapElement,
  ObjectState,
  PresentationElement,
  PresentationView,
  ShapeElement,
  TextElement
} from '@/maps/types/api'

import { aMap, aState, newMapView } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

// Typed element builders — createElement returns the union, so narrow by kind
// before layering overrides on the concrete shape (no `any`, no casts).
function textElement(overrides: Partial<TextElement> = {}): TextElement {
  const el = createElement('text', 100, 100)
  if (el.kind !== 'text') {
    throw new Error('expected text element')
  }
  return { ...el, ...overrides }
}
function shapeElement(kind: 'rect' | 'line', overrides: Partial<ShapeElement> = {}): ShapeElement {
  const el = createElement(kind, 100, 100)
  if (el.kind !== 'shape') {
    throw new Error('expected shape element')
  }
  return { ...el, ...overrides }
}
function dataElement(overrides: Partial<DataElement> = {}): DataElement {
  const el = createElement('data', 100, 100)
  if (el.kind !== 'data') {
    throw new Error('expected data element')
  }
  return { ...el, ...overrides }
}

function presentationView(elements: PresentationElement[]): PresentationView {
  return { ...newMapView('presentation'), elements } as PresentationView
}

function makeConfig(elements: PresentationElement[], name = 'pres'): MapConfig {
  return aMap({ name, alias: 'Pres', view: presentationView(elements) })
}

function upState(id: string): Record<string, ObjectState> {
  return {
    [id]: aState({
      object_id: id,
      type: 'host',
      state: 'UP',
      output: 'PING OK',
      perf_data: '',
      acknowledged: false,
      in_downtime: false,
      stale: false
    })
  }
}

// Edit-mode chrome (inspector, gallery, data panel, confirm dialog) is not under
// test here; stubbing it keeps the focus on the canvas's own element rendering,
// selection and palette wiring.
const editStubs = {
  PresentationInspectorPanel: true,
  PresentationTemplateGallery: true,
  PresentationDataPanel: true,
  MapsConfirmDialog: true
}
// Connectors and their value labels live in their own SVG overlay; stub them so
// the split between the inline element layer and the overlay is countable.
const connectorStubs = { PresentationConnector: true, PresentationConnectorLabels: true }

describe('PresentationCanvas', () => {
  beforeEach(() => {
    // useSlideViewport observes the viewport for zoom-to-fit; jsdom has no
    // ResizeObserver, and the canvas never needs real layout here.
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })
  afterEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  it('renders one element view per document element (view mode)', () => {
    const config = makeConfig([textElement({ text: 'Alpha' }), shapeElement('rect'), dataElement()])
    const { container } = render(PresentationCanvas, {
      props: { config, states: {}, editMode: false },
      global: mapsGlobal()
    })

    expect(container.querySelectorAll('.maps-presentation-canvas__el')).toHaveLength(3)
    // The text element's content is rendered by the real element view.
    expect(screen.getByText('Alpha')).toBeInTheDocument()
  })

  it('renders connectors in the overlay, not the inline element layer', () => {
    const config = makeConfig([textElement({ text: 'Label' }), shapeElement('line')])
    const { container } = render(PresentationCanvas, {
      props: { config, states: {}, editMode: false },
      global: mapsGlobal(connectorStubs)
    })

    // Only the text box is an inline element; the line is a connector.
    expect(container.querySelectorAll('.maps-presentation-canvas__el')).toHaveLength(1)
    expect(container.querySelectorAll('presentation-connector-stub')).toHaveLength(1)
    expect(container.querySelectorAll('presentation-connector-labels-stub')).toHaveLength(1)
  })

  it('omits hidden elements in view mode but keeps them while editing', () => {
    const hidden = textElement({ text: 'Secret', hidden: true })
    const visible = textElement({ text: 'Shown' })

    const view = render(PresentationCanvas, {
      props: { config: makeConfig([hidden, visible]), states: {}, editMode: false },
      global: mapsGlobal()
    })
    expect(screen.getByText('Shown')).toBeInTheDocument()
    expect(screen.queryByText('Secret')).toBeNull()
    view.unmount()

    render(PresentationCanvas, {
      props: { config: makeConfig([hidden, visible]), states: {}, editMode: true },
      global: mapsGlobal(editStubs)
    })
    // Hidden elements stay in the DOM (dimmed) while editing so they remain reachable.
    expect(screen.getByText('Secret')).toBeInTheDocument()
  })

  it('exposes a bound element as an accessible drill-down button and emits object-click', async () => {
    const user = userEvent.setup()
    const bound = dataElement({ host_name: 'localhost' })
    const config = makeConfig([bound])
    const clicked = ref<MapElement | null>(null)

    render(
      defineComponent({
        components: { PresentationCanvas },
        setup() {
          return {
            config,
            states: upState(bound.id),
            onObjectClick: (obj: MapElement) => {
              clicked.value = obj
            }
          }
        },
        template: `
          <PresentationCanvas
            :config="config"
            :states="states"
            :edit-mode="false"
            @object-click="onObjectClick"
          />
        `
      }),
      { global: mapsGlobal() }
    )

    // Bound elements act like map objects in view mode: name + live state word.
    const button = screen.getByRole('button', { name: 'localhost, Up' })
    await user.click(button)

    expect(clicked.value).toMatchObject({ id: bound.id, type: 'host', host_name: 'localhost' })
  })

  it('does not turn unbound elements into drill-down buttons in view mode', () => {
    const config = makeConfig([textElement({ text: 'Deco' }), dataElement()])
    render(PresentationCanvas, {
      props: { config, states: {}, editMode: false },
      global: mapsGlobal()
    })

    expect(screen.queryByRole('button')).toBeNull()
  })

  it('selects an element on pointer-down while editing', async () => {
    const config = makeConfig([shapeElement('rect')])
    const { container } = render(PresentationCanvas, {
      props: { config, states: {}, editMode: true },
      global: mapsGlobal(editStubs)
    })

    const el = container.querySelector('.maps-presentation-canvas__el')
    expect(el).not.toBeNull()
    expect(el!.classList.contains('maps-presentation-canvas__el--selected')).toBe(false)

    await fireEvent.pointerDown(el!)

    await waitFor(() =>
      expect(el!.classList.contains('maps-presentation-canvas__el--selected')).toBe(true)
    )
  })

  it('inserts a new element from the palette while editing', async () => {
    const user = userEvent.setup()
    const config = makeConfig([], 'empty')
    // Suppress the one-time template gallery so the palette is the active surface.
    sessionStorage.setItem('maps-pres-templates-seen:empty', '1')
    const { container } = render(PresentationCanvas, {
      props: { config, states: {}, editMode: true },
      global: mapsGlobal(editStubs)
    })

    expect(container.querySelectorAll('.maps-presentation-canvas__el')).toHaveLength(0)
    expect(screen.getByText('Pick a tool above to start your slide')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Text' }))

    expect(container.querySelectorAll('.maps-presentation-canvas__el')).toHaveLength(1)
  })

  it('lists top-level elements by name in the layers panel', async () => {
    const user = userEvent.setup()
    const config = makeConfig([shapeElement('rect', { name: 'Core switch' }), textElement()])
    render(PresentationCanvas, {
      props: { config, states: {}, editMode: true },
      global: mapsGlobal(editStubs)
    })

    // The element name is not painted on the shape itself — only the layers
    // panel shows it, so finding it proves the panel opened and listed it.
    expect(screen.queryByText('Core switch')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Layers' }))
    expect(screen.getByText('Core switch')).toBeInTheDocument()
  })
})
