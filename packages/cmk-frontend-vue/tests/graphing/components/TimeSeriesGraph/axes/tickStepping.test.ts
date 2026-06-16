/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  alignedDomain,
  stepIncrements
} from '@/graphing/components/TimeSeriesGraph/axes/tickStepping'

describe('alignedDomain', () => {
  test('rounds a domain outward to a nice step', () => {
    const domain: [number, number] = [3, 97]

    const result = alignedDomain(domain, 5, stepIncrements('decimal'))

    expect(result).toEqual([0, 100, 20])
  })

  test('rounds a negative domain outward to a nice step', () => {
    const domain: [number, number] = [-97, -23]

    const result = alignedDomain(domain, 5, stepIncrements('decimal'))

    expect(result).toEqual([-100, -20, 20])
  })

  test('orders reversed input bounds', () => {
    const domain: [number, number] = [10, 2]

    const [start, end] = alignedDomain(domain, 4, stepIncrements('decimal'))

    expect(start).toBeLessThan(end)
  })

  test('separates equal bounds so the step stays finite', () => {
    const domain: [number, number] = [5, 5]

    const [start, end, step] = alignedDomain(domain, 4, stepIncrements('decimal'))

    expect(start).toBeLessThan(end)
    expect(Number.isFinite(step)).toBe(true)
  })

  test('treats non-finite bounds as zero', () => {
    const domain: [number, number] = [NaN, 10]

    const [start] = alignedDomain(domain, 5, stepIncrements('decimal'))

    expect(start).toBe(0)
  })

  test('uses a binary ladder when given one', () => {
    const domain: [number, number] = [0, 100]

    const [, , decimalStep] = alignedDomain(domain, 4, stepIncrements('decimal'))
    const [, , binaryStep] = alignedDomain(domain, 4, stepIncrements('binary'))

    expect(decimalStep).not.toBe(binaryStep)
  })
})
