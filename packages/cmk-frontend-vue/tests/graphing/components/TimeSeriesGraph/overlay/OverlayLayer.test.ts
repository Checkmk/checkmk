/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { beforeEach, expect, test, vi } from 'vitest'

import type {
  HoverSample,
  HoverState
} from '@/graphing/components/TimeSeriesGraph/interaction/hover'
import OverlayLayer from '@/graphing/components/TimeSeriesGraph/overlay/OverlayLayer.vue'

let dotCentres: Array<[number, number]> = []

function canvasContextRecordingDotCentres(): CanvasRenderingContext2D {
  const state: Record<string | symbol, unknown> = {}
  return new Proxy(state, {
    get: (target, prop) => {
      if (prop === 'arc') {
        return (x: number, y: number) => void dotCentres.push([x, y])
      }
      return prop in target ? target[prop] : () => undefined
    },
    set: (target, prop, value) => {
      target[prop] = value
      return true
    }
  }) as unknown as CanvasRenderingContext2D
}

function stubMatchMediaMissingFromJsdom(): void {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    })
  )
}

beforeEach(() => {
  dotCentres = []
  stubMatchMediaMissingFromJsdom()
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
    canvasContextRecordingDotCentres()
  )
})

function makeSample(metricName: string, drawnPoint: { x: number; y: number }): HoverSample {
  return {
    metricName,
    label: metricName,
    color: '#ff0000',
    formattedValue: '1',
    attributes: [],
    drawnPoint,
    snapTime: null,
    isClosest: false
  }
}

test('draws each focus dot where its own sample is, not on the shared crosshair', () => {
  const crosshairX = 40
  const samples = [makeSample('rising', { x: 30, y: 20 }), makeSample('falling', { x: 60, y: 70 })]
  const hoverState: HoverState = {
    cursorX: crosshairX,
    cursorY: 50,
    clientX: crosshairX,
    clientY: 50,
    snapX: crosshairX,
    snapTime: 40,
    samples
  }

  render(OverlayLayer, { props: { hoverState, plotWidth: 100, plotHeight: 100, pinX: null } })

  expect(dotCentres).toEqual(samples.map((sample) => [sample.drawnPoint!.x, sample.drawnPoint!.y]))
})
