/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  stepIncrements,
  valueDomain
} from '@/graphing/components/TimeSeriesGraph/axes/tickStepping'

describe('valueDomain', () => {
  test('rounds a domain outward to a nice step', () => {
    const domain: [number, number] = [3, 97]

    const result = valueDomain(domain, 5, stepIncrements('decimal'))

    expect(result).toEqual([0, 100, 20])
  })

  test('rounds a negative domain outward to a nice step', () => {
    const domain: [number, number] = [-97, -23]

    const result = valueDomain(domain, 5, stepIncrements('decimal'))

    expect(result).toEqual([-100, -20, 20])
  })

  test('orders reversed input bounds', () => {
    const domain: [number, number] = [10, 2]

    const [start, end] = valueDomain(domain, 4, stepIncrements('decimal'))

    expect(start).toBeLessThan(end)
  })

  test('separates equal bounds so the step stays finite', () => {
    const domain: [number, number] = [5, 5]

    const [start, end, step] = valueDomain(domain, 4, stepIncrements('decimal'))

    expect(start).toBeLessThan(end)
    expect(Number.isFinite(step)).toBe(true)
  })

  test('treats non-finite bounds as zero', () => {
    const domain: [number, number] = [NaN, 10]

    const [start] = valueDomain(domain, 5, stepIncrements('decimal'))

    expect(start).toBe(0)
  })

  test('uses a binary ladder when given one', () => {
    const domain: [number, number] = [0, 100]

    const [, , decimalStep] = valueDomain(domain, 4, stepIncrements('decimal'))
    const [, , binaryStep] = valueDomain(domain, 4, stepIncrements('binary'))

    expect(decimalStep).not.toBe(binaryStep)
  })
})

describe('valueDomain - explicit mode', () => {
  test('keeps the given bounds where aligned mode would round them outward', () => {
    const domain: [number, number] = [1, 5]

    // With few ticks the aligned mode snaps [1, 5] out to [0, 6]; explicit must not.
    const aligned = valueDomain(domain, 2, stepIncrements('decimal'), 'aligned')
    const explicit = valueDomain(domain, 2, stepIncrements('decimal'), 'explicit')

    expect([aligned[0], aligned[1]]).toEqual([0, 6])
    expect([explicit[0], explicit[1]]).toEqual([1, 5])
  })

  test('preserves non-round bounds verbatim', () => {
    const domain: [number, number] = [3, 97]

    const [start, end] = valueDomain(domain, 5, stepIncrements('decimal'), 'explicit')

    expect([start, end]).toEqual([3, 97])
  })

  test('still returns a finite tick step for the forced range', () => {
    const domain: [number, number] = [1, 5]

    const [, , step] = valueDomain(domain, 2, stepIncrements('decimal'), 'explicit')

    expect(step).toBeGreaterThan(0)
    expect(Number.isFinite(step)).toBe(true)
  })

  test('still orders reversed input bounds', () => {
    const domain: [number, number] = [5, 1]

    const [start, end] = valueDomain(domain, 4, stepIncrements('decimal'), 'explicit')

    expect([start, end]).toEqual([1, 5])
  })

  test('still separates equal bounds so the step stays finite', () => {
    const domain: [number, number] = [5, 5]

    const [start, end, step] = valueDomain(domain, 4, stepIncrements('decimal'), 'explicit')

    expect(start).toBeLessThan(end)
    expect(Number.isFinite(step)).toBe(true)
  })
})
