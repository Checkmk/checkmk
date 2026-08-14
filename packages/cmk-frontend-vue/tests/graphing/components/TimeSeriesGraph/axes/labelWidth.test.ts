/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { measureAxisLabel } from '@/graphing/components/TimeSeriesGraph/axes/labelWidth'

const advanceByText = new Map<string, number>()
const contextStub = {
  font: '',
  measureText: (text: string) => ({ width: advanceByText.get(text) ?? 0 })
} as unknown as CanvasRenderingContext2D

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(contextStub)
})

afterEach(() => {
  vi.restoreAllMocks()
  advanceByText.clear()
})

function axisReference(letterSpacing: string): HTMLElement {
  const reference = document.createElement('div')
  reference.style.setProperty('--font-size-small', '10px')
  reference.style.letterSpacing = letterSpacing
  document.body.appendChild(reference)
  return reference
}

describe('measureAxisLabel', () => {
  test('adds the letter spacing the browser draws around each glyph', () => {
    advanceByText.set('9.31 GiB', 38)

    expect(measureAxisLabel('9.31 GiB', axisReference('0.5px'))).toBeCloseTo(42)
  })

  test('measures unspaced text at its bare advance width', () => {
    advanceByText.set('7.45 GiB', 38.92)

    expect(measureAxisLabel('7.45 GiB', axisReference('normal'))).toBeCloseTo(38.92)
  })

  test('spaces out the per-character estimate it falls back to without a canvas measurement', () => {
    advanceByText.set('5.59 GiB', 0)
    const estimatedAdvance = '5.59 GiB'.length * 10 * 0.6

    expect(measureAxisLabel('5.59 GiB', axisReference('0.5px'))).toBeCloseTo(estimatedAdvance + 4)
  })

  test('keeps the measurements of differently spaced references apart', () => {
    advanceByText.set('1.12 GiB', 35.49)

    const spaced = measureAxisLabel('1.12 GiB', axisReference('0.5px'))
    const unspaced = measureAxisLabel('1.12 GiB', axisReference('normal'))

    expect(spaced - unspaced).toBeCloseTo(4)
  })
})
