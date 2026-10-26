/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { type EffectScope, effectScope, nextTick, shallowRef } from 'vue'

import { useCanvasViewport } from '@/maps/map/static/composables/useCanvasViewport'

import { aMap, newMapView } from '../../../support/fixtures'

/** Resizes an element and reports it, the way the browser would. */
let report: (target: Element, width: number, height: number) => void = () => {}

/** jsdom lays nothing out, so an element's client size is whatever was last reported. */
function sizedLike(element: HTMLElement, size: { width: number; height: number }): void {
  Object.defineProperty(element, 'clientWidth', { get: () => size.width })
  Object.defineProperty(element, 'clientHeight', { get: () => size.height })
}

const paneBox = { width: 1000, height: 600 }

class ReportingResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    report = (target, width, height) => {
      paneBox.width = width
      paneBox.height = height
      callback(
        [
          {
            target,
            contentBoxSize: [{ inlineSize: width, blockSize: height }]
          } as unknown as ResizeObserverEntry
        ],
        this as unknown as ResizeObserver
      )
    }
  }
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

let scope: EffectScope | null = null
let pane: HTMLElement | null = null

afterEach(() => {
  scope?.stop()
  pane?.remove()
})

/** A default-renderer canvas inside a 1000×600 scrolling pane. */
async function viewportInPane() {
  vi.stubGlobal('ResizeObserver', ReportingResizeObserver)
  const host = document.body.appendChild(document.createElement('div'))
  pane = host
  host.style.overflow = 'auto'
  paneBox.width = 1000
  paneBox.height = 600
  sizedLike(host, paneBox)
  const canvas = shallowRef<HTMLElement | null>(host.appendChild(document.createElement('div')))
  scope = effectScope()
  const viewport = scope.run(() =>
    useCanvasViewport({
      canvas,
      config: () => aMap({ name: 'm', view: newMapView('static') }),
      width: () => 1000,
      height: () => 600,
      editMode: () => false,
      preview: () => false,
      classic: () => false,
      backgroundUrl: () => null,
      backgroundSize: () => null
    })
  )!
  await nextTick()
  return { pane: host, viewport }
}

function backgroundStyle(backgroundSize: { width: number; height: number } | null): string {
  const config = aMap({
    name: 'test',
    view: newMapView('static'),
    background_image: 'floor.png',
    objects: []
  })
  const local = effectScope()
  const viewport = local.run(() =>
    useCanvasViewport({
      canvas: shallowRef(null),
      config: () => config,
      width: () => 1150,
      height: () => 850,
      editMode: () => false,
      preview: () => false,
      classic: () => backgroundSize !== null,
      backgroundUrl: () => 'floor.png',
      backgroundSize: () => backgroundSize
    })
  )
  const style = viewport?.style.value.backgroundSize ?? ''
  local.stop()
  return style
}

describe('useCanvasViewport', () => {
  it('keeps the pane it had unzoomed while scrollbars shrink it under a zoom', async () => {
    const { pane, viewport } = await viewportInPane()

    viewport.zoom.value = 2
    report(pane, 985, 585)
    await nextTick()

    expect(viewport.restingPane.value).toEqual({ width: 1000, height: 600 })
    expect(viewport.style.value).toMatchObject({ width: '1000px', height: '600px', zoom: '2' })
  })

  it('follows the pane while unzoomed', async () => {
    const { pane, viewport } = await viewportInPane()

    report(pane, 800, 500)
    await nextTick()

    expect(viewport.restingPane.value).toEqual({ width: 800, height: 500 })
  })

  // The canvas may be larger than the image when objects lie beyond it; the
  // image must not stretch along.
  it('draws a background at its own size where the renderer uses that size', () => {
    expect(backgroundStyle({ width: 640, height: 480 })).toBe('640px 480px')
  })

  it('stretches the background over the canvas otherwise', () => {
    expect(backgroundStyle(null)).toBe('100% 100%')
  })
})
