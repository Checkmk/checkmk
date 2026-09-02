/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, ref } from 'vue'

import MapCanvas from '@/maps/map/static/components/MapCanvas.vue'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'

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

// Smoke test for the full render path: real MapElement children (not stubbed),
// so a regression anywhere in the static map's object rendering fails here.
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
