/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'

import MapCanvas from '@/maps/map/static/components/MapCanvas.vue'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { MAX_PULSES } from '@/maps/utils/problemState'

import { aMap, aState, anObject, newMapView } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

// MapCanvas renders MapZoomResetPill, which teleports to #app. Stub the
// teleport per render (no teleport target needed in jsdom).
const overlayStubs = { HoverMenu: true, ContextMenu: true, teleport: true }
const stubs = { ...overlayStubs, MapElement: true, MapLine: true }

const sampleConfig: MapConfig = aMap({
  name: 'test',
  alias: 'Test',
  icon_size: 30,
  connection_id: 'test',
  rotation_interval: 0,
  sort_order: 0,
  click_action: 'link',
  view: newMapView('static'),
  objects: [
    anObject({
      id: '1',
      type: 'host',
      x: 100,
      y: 200,
      host_name: 'localhost',
      label: {
        show: true,
        x: 0,
        y: 0,
        size: 10,
        color: '#ffffff',
        background: 'transparent'
      },
      display: { mode: 'icon' },
      z: 1
    })
  ]
})

const sampleStates: Record<string, ObjectState> = {
  '1': aState({
    object_id: '1',
    type: 'host',
    state: 'UP',
    output: 'PING OK',
    acknowledged: false,
    in_downtime: false,
    stale: false
  })
}

const baseProps = {
  config: sampleConfig,
  states: sampleStates,
  editMode: false,
  placing: false,
  lineDragPositions: {},
  selectedObjectId: null
}

describe('MapCanvas', () => {
  // The pointer shape is style state with no accessible representation.
  it('shows an administrator a clickable object outside the editor, not one to drag', () => {
    render(MapCanvas, { props: { ...baseProps, isAdmin: true }, global: mapsGlobal(overlayStubs) })

    const object = screen.getByRole('button', { name: 'localhost, Up' })
    expect(object.closest<HTMLElement>('[data-object-id]')!.style.cursor).toBe('pointer')
  })

  it('renders each object as an accessible button named "<name>, <state word>"', () => {
    render(MapCanvas, { props: baseProps, global: mapsGlobal(stubs) })

    expect(screen.getAllByRole('button')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'localhost, Up' })).toBeInTheDocument()
  })

  const aLine = (id: string, z: number | null = null) =>
    anObject({
      id,
      type: 'line' as const,
      x: 0,
      y: 0,
      x2: 50,
      y2: 50,
      label: { show: false, x: 0, y: 0, size: 10, color: '#fff', background: 'transparent' },
      url_target: '_blank',
      ...(z === null ? {} : { z })
    })

  it('buckets lines into one z-indexed SVG layer per distinct z', () => {
    const line = aLine
    const { container } = render(MapCanvas, {
      props: {
        ...baseProps,
        // default_z=10 so the z-less line shares a layer with the z=10 line.
        config: {
          ...sampleConfig,
          default_z: 10,
          objects: [line('a', 2), line('b', 20), line('c', null), line('d', 10)]
        }
      },
      global: mapsGlobal(stubs)
    })
    // Geometry: z-layer bucketing has no accessible representation, so this
    // stays a container-scoped DOM query.
    const zLayers = [...container.querySelectorAll('svg')]
      .map((s) => s.getAttribute('style') ?? '')
      .filter((style) => style.includes('z-index'))
      .map((style) => parseInt(style.match(/z-index:\s*(\d+)/)?.[1] ?? '', 10))
    // Three distinct buckets (2, 10, 20) sorted ascending; z-less + z=10 merge.
    expect(zLayers).toEqual([2, 10, 20])
  })

  it('tags a line once, so a lookup by object id does not find it twice', () => {
    const { container } = render(MapCanvas, {
      props: { ...baseProps, config: { ...sampleConfig, objects: [aLine('a')] } },
      // The real MapLine carries the id on its own root; stubbed out, a second
      // one on the wrapper would be the only match and hide the duplicate.
      global: mapsGlobal(overlayStubs)
    })

    expect(container.querySelectorAll('[data-object-id="a"]')).toHaveLength(1)
  })

  it('opens a line the way it opens an icon: on a double click', async () => {
    const { container, emitted } = render(MapCanvas, {
      props: { ...baseProps, editMode: true, config: { ...sampleConfig, objects: [aLine('a')] } },
      global: mapsGlobal(overlayStubs)
    })

    const line = container.querySelector('[data-object-id="a"] polyline')!
    await fireEvent.dblClick(line)

    expect(emitted('object-dblclick')).toHaveLength(1)
  })

  it('fires the click contract via keyboard: focus the object, press Enter', async () => {
    // Map objects are reachable and activatable without a pointer. The
    // object-click emit is the click contract, captured through a host-wrapper
    // handler.
    const user = userEvent.setup()
    const clicked = ref<MapElement | null>(null)
    render(
      defineComponent({
        components: { MapCanvas },
        setup() {
          const onObjectClick = (obj: MapElement) => {
            clicked.value = obj
          }
          return { baseProps, onObjectClick }
        },
        template: `<MapCanvas v-bind="baseProps" @object-click="onObjectClick" />`
      }),
      { global: mapsGlobal(stubs) }
    )

    const obj = screen.getByRole('button', { name: 'localhost, Up' })
    obj.focus()
    await user.keyboard('{Enter}')

    expect(clicked.value).toMatchObject({ id: '1', type: 'host', host_name: 'localhost' })
  })
})

describe('MapCanvas – context menu', () => {
  it('hands the focus back to the object the menu was opened on', async () => {
    const user = userEvent.setup()
    render(MapCanvas, {
      props: { ...baseProps, checkmkUrl: 'http://checkmk/site/check_mk/' },
      global: mapsGlobal({ HoverMenu: true, teleport: true, MapElement: true, MapLine: true })
    })
    const object = screen.getByRole('button', { name: 'localhost, Up' })

    await user.pointer({ keys: '[MouseRight]', target: object })
    await waitFor(() =>
      expect(screen.getByRole('menuitem', { name: 'State of host' })).toHaveFocus()
    )
    await user.keyboard('{Escape}')

    await waitFor(() => expect(object).toHaveFocus())
  })
})

// Smoke test for the full render path: real MapElement children (not stubbed),
// so a regression anywhere in the static map's object rendering fails here.
describe('MapCanvas – placing', () => {
  it('reports the placement once, not again with the click that ends it', async () => {
    const { emitted } = render(MapCanvas, {
      props: { ...baseProps, editMode: true, placing: true },
      global: mapsGlobal(stubs)
    })
    const canvas = screen.getByRole('group', { name: 'Map canvas' })

    await fireEvent.pointerDown(canvas, { button: 0 })
    await fireEvent.pointerUp(canvas, { button: 0 })
    await fireEvent.click(canvas)

    expect(emitted()['canvas-click']).toHaveLength(1)
  })
})

describe('MapCanvas – smoke with real MapElement', () => {
  const smokeConfig: MapConfig = aMap({
    ...sampleConfig,
    objects: [
      ...sampleConfig.objects,
      anObject({
        id: '2',
        type: 'textbox',
        x: 300,
        y: 100,
        label: {
          show: true,
          text: 'Hello map',
          x: 0,
          y: 0,
          size: 13,
          color: '#ffffff',
          background: 'transparent'
        },
        z: 1
      })
    ]
  })

  beforeEach(() => {})

  /** The state token the icon paints its disc, glow and outline from. */
  function stateColorTokenOf(container: Element): string | undefined {
    return container
      .querySelector<SVGElement>('.maps-map-element-state-icon')
      ?.style.getPropertyValue('--maps-map-element-state-icon-color')
  }

  /** As many hosts as given, all DOWN, so each calls for the pulse. */
  function downHosts(count: number): { config: MapConfig; states: Record<string, ObjectState> } {
    const ids = Array.from({ length: count }, (_, i) => `d${i}`)
    return {
      config: aMap({
        ...sampleConfig,
        objects: ids.map((id, i) =>
          anObject({ id, type: 'host', x: i, y: 0, host_name: id, display: { mode: 'icon' } })
        )
      }),
      states: Object.fromEntries(
        ids.map((id) => [id, aState({ object_id: id, type: 'host', state: 'DOWN' })])
      )
    }
  }

  /**
   * Whether the pulses rest is style state with no accessible representation.
   * The pulses count themselves once mounted, so the canvas follows a tick later.
   */
  async function pulsesRest(): Promise<boolean> {
    await nextTick()
    return screen.getByRole('group', { name: 'Map canvas' }).hasAttribute('data-map-pulses-rest')
  }

  it.each([
    [MAX_PULSES, false],
    [MAX_PULSES + 1, true]
  ])('with %i hosts down, lets the pulses rest: %s', async (down, rests) => {
    render(MapCanvas, {
      props: { ...baseProps, ...downHosts(down) },
      global: mapsGlobal(overlayStubs)
    })

    expect(await pulsesRest()).toBe(rests)
  })

  it('counts no pulse for a state whose object the map does not draw', async () => {
    const { config, states } = downHosts(MAX_PULSES)
    const undrawn = aState({ object_id: 'gone', type: 'host', state: 'DOWN' })
    render(MapCanvas, {
      props: { ...baseProps, config, states: { ...states, gone: undrawn } },
      global: mapsGlobal(overlayStubs)
    })

    expect(await pulsesRest()).toBe(false)
  })

  it("cuts the label of a grid's object off at the next object in the row", () => {
    const label = { show: true, x: 0, y: 0, size: 10, color: '#ffffff', background: 'transparent' }
    const config = aMap({
      ...sampleConfig,
      objects: [
        anObject({ id: 'g', type: 'grid', x: 0, y: 0, grid_offset_x: 50, label }),
        anObject({
          id: 'auto:grid:g:web01',
          type: 'host',
          x: 0,
          y: 0,
          host_name: 'web01',
          grid_id: 'g',
          label
        })
      ]
    })
    render(MapCanvas, {
      props: { ...baseProps, config, states: {} },
      global: mapsGlobal(overlayStubs)
    })

    expect(screen.getByText('web01').style.maxWidth).toBe(
      'calc(50px * var(--maps-canvas-scale-x, 1) - var(--dimension-2) - 2 * var(--dimension-4))'
    )
  })

  it('renders host icon and textbox content', () => {
    const { container } = render(MapCanvas, {
      props: { ...baseProps, config: smokeConfig },
      global: mapsGlobal(overlayStubs)
    })

    // Host with its state word, textbox by its visual-only name.
    expect(screen.getByRole('button', { name: 'localhost, Up' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hello map' })).toBeInTheDocument()
    expect(screen.getByText('Hello map')).toBeInTheDocument()
    // Which colour the icon paints has no accessible representation, and the
    // value itself belongs to the theme — so what is pinned is the state token
    // the icon hands to its own styling.
    expect(stateColorTokenOf(container)).toBe('var(--color-state-up)')
  })

  it('leaves an object without a problem out of a map showing only problems', () => {
    const config = aMap({
      ...sampleConfig,
      objects: [
        ...sampleConfig.objects,
        anObject({ id: '2', type: 'host', x: 300, y: 200, host_name: 'db01', z: 1 })
      ]
    })
    const states = {
      ...sampleStates,
      '2': aState({ object_id: '2', type: 'host', state: 'DOWN' })
    }
    render(MapCanvas, {
      props: { ...baseProps, config, states, problemsOnly: true },
      global: mapsGlobal(stubs)
    })

    expect(screen.getByRole('button', { name: 'db01, Down' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'localhost, Up' })).toBeNull()
  })

  it('reflects a state change (UP → DOWN) in icon colour and accessible name', async () => {
    const { container, rerender } = render(MapCanvas, {
      props: { ...baseProps, config: smokeConfig },
      global: mapsGlobal(overlayStubs)
    })

    await rerender({
      ...baseProps,
      config: smokeConfig,
      states: {
        '1': { ...sampleStates['1']!, state: 'DOWN', output: 'PING CRITICAL' }
      }
    })

    expect(screen.getByRole('button', { name: 'localhost, Down' })).toBeInTheDocument()
    expect(stateColorTokenOf(container)).toBe('var(--color-state-down)')
  })
})

// Wheel-zoom interaction (view mode). Locks the zoom range [1×, 4×], the
// pannable-cursor state that tracks it, and that zoom is disabled while editing.
// Zoom factor and pannable cursor are style/class state with no accessible
// representation of their own, so they are read off the canvas element.
describe('MapCanvas – wheel zoom', () => {
  beforeEach(() => {})

  function renderCanvas(overrides: Partial<typeof baseProps> = {}) {
    render(MapCanvas, {
      props: { ...baseProps, ...overrides },
      global: mapsGlobal(stubs)
    })
    return screen.getByRole('group', { name: 'Map canvas' })
  }

  // No clientX/Y: the handler only reads them when a scroll ancestor exists,
  // which a detached test render has not.
  const zoomIn = (canvas: Element) => fireEvent.wheel(canvas, { deltaY: -100 })
  const zoomOut = (canvas: Element) => fireEvent.wheel(canvas, { deltaY: 100 })

  it('starts at fit (no zoom, not pannable)', () => {
    const canvas = renderCanvas()
    expect(canvas).not.toHaveClass('maps-map-canvas--pannable')
    expect(canvas.getAttribute('style') ?? '').not.toContain('zoom')
  })

  it('zooms in on wheel-up and marks the canvas pannable', async () => {
    const canvas = renderCanvas()
    await zoomIn(canvas)
    expect(canvas).toHaveClass('maps-map-canvas--pannable')
    expect(canvas.getAttribute('style')).toContain('zoom')
  })

  it('clamps zoom-in at 4×', async () => {
    const canvas = renderCanvas()
    for (let i = 0; i < 40; i++) {
      await zoomIn(canvas)
    }
    expect(canvas.getAttribute('style')).toMatch(/zoom:\s*4\b/)
  })

  it('clamps zoom-out back to fit and clears the pannable cursor', async () => {
    const canvas = renderCanvas()
    for (let i = 0; i < 10; i++) {
      await zoomIn(canvas)
    }
    for (let i = 0; i < 40; i++) {
      await zoomOut(canvas)
    }
    expect(canvas).not.toHaveClass('maps-map-canvas--pannable')
    expect(canvas.getAttribute('style') ?? '').not.toContain('zoom')
  })

  it('does not zoom while editing', async () => {
    const canvas = renderCanvas({ editMode: true })
    await zoomIn(canvas)
    expect(canvas).not.toHaveClass('maps-map-canvas--pannable')
    expect(canvas.getAttribute('style') ?? '').not.toContain('zoom')
  })
})

describe('MapCanvas – resizing a grid', () => {
  const member = (name: string, x: number): MapElement =>
    anObject({ id: `auto:grid:g:${name}`, type: 'host', host_name: name, grid_id: 'g', x, y: 100 })

  function renderGrid(props: { editMode: boolean; selectedIds: string[] }) {
    const config = aMap({
      ...sampleConfig,
      objects: [
        anObject({ id: 'g', type: 'grid', x: 100, y: 100, grid_per_row: 3, grid_offset_x: 50 }),
        member('a', 100),
        member('b', 150),
        member('c', 200)
      ]
    })
    return render(MapCanvas, {
      props: { ...baseProps, config, states: {}, ...props },
      global: mapsGlobal(stubs)
    })
  }

  const grip = () => screen.queryByTitle('Drag to change the objects per row')

  it('offers the grip on the frame of a grid selected in the editor only', () => {
    const unselected = renderGrid({ editMode: true, selectedIds: [] })
    expect(grip()).toBeNull()
    unselected.unmount()

    renderGrid({ editMode: false, selectedIds: ['g'] })
    expect(grip()).toBeNull()
  })

  // Where the last row is full, the last object's label hangs over the grip.
  it('lifts a grid selected in the editor above its objects', () => {
    const { container } = renderGrid({ editMode: true, selectedIds: ['g'] })
    const z = (id: string) =>
      Number(container.querySelector<HTMLElement>(`[data-object-id="${id}"]`)!.style.zIndex)

    expect(z('g')).toBeGreaterThan(z('auto:grid:g:c'))
  })

  it('lays the grid out anew while its grip is dragged, and saves it once let go', async () => {
    const { container, emitted } = renderGrid({ editMode: true, selectedIds: ['g'] })
    const canvas = container.querySelector<HTMLElement>('.maps-map-canvas')!
    canvas.setPointerCapture = () => {}

    // jsdom lays nothing out, so how far the pointer goes is beyond measure:
    // any move to the left takes the grid to a single column.
    await fireEvent.pointerDown(grip()!, { clientX: 300, pointerId: 1 })
    await fireEvent.pointerMove(canvas, { clientX: 250, pointerId: 1 })
    await fireEvent.pointerUp(canvas, { clientX: 250, pointerId: 1 })

    expect(emitted()['grid-resize']).toEqual([['g', 1]])
    expect(emitted()['grid-resize-end']).toEqual([['g', 1]])
  })
})

describe('MapCanvas – a grid outside the editor', () => {
  const member = (name: string, x: number): MapElement =>
    anObject({ id: `auto:grid:g:${name}`, type: 'host', host_name: name, grid_id: 'g', x, y: 100 })

  const config = aMap({
    ...sampleConfig,
    objects: [
      anObject({ id: 'g', type: 'grid', x: 100, y: 100, grid_per_row: 2, grid_offset_x: 50 }),
      member('a', 100),
      member('b', 150)
    ]
  })

  it('shows the frame of a grid while the pointer is on its objects', async () => {
    const user = userEvent.setup()
    render(MapCanvas, {
      props: { ...baseProps, config, states: {} },
      global: mapsGlobal(overlayStubs)
    })
    expect(screen.queryByText('Grid · 2 hosts')).toBeNull()
    // The pointer is on the object where it is drawn, inside its box.
    const drawn = screen.getByRole('button', { name: /^a,/ }).firstElementChild!

    await user.hover(drawn)
    expect(screen.getByText('Grid · 2 hosts')).toBeInTheDocument()

    await user.unhover(drawn)
    await waitFor(() => expect(screen.queryByText('Grid · 2 hosts')).toBeNull())
  })
})
