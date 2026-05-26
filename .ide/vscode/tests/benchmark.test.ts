/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type BenchmarkRun,
  HISTORY_CAP,
  appendRun,
  detectRegression
} from '../src/benchmark/startup'

function run(totalMs: number, overrides: Partial<BenchmarkRun> = {}): BenchmarkRun {
  return {
    ts: overrides.ts ?? Date.now(),
    version: overrides.version ?? '0.1.0',
    branch: overrides.branch ?? 'master',
    totalMs,
    phases: overrides.phases ?? { fetch: totalMs }
  }
}

function manyRuns(values: number[]): BenchmarkRun[] {
  return values.map((v) => run(v))
}

describe('appendRun', () => {
  it('appends a run', () => {
    const out = appendRun([], run(100))
    expect(out).toHaveLength(1)
    expect(out[0].totalMs).toBe(100)
  })

  it('caps history at HISTORY_CAP entries (oldest dropped first)', () => {
    let h: BenchmarkRun[] = []
    for (let i = 0; i < HISTORY_CAP + 10; i++) h = appendRun(h, run(i))
    expect(h).toHaveLength(HISTORY_CAP)
    // First entry should be run(10), since 0..9 were trimmed.
    expect(h[0].totalMs).toBe(10)
    expect(h[h.length - 1].totalMs).toBe(HISTORY_CAP + 9)
  })

  it('returns a new array (does not mutate input)', () => {
    const input: BenchmarkRun[] = []
    const out = appendRun(input, run(50))
    expect(out).not.toBe(input)
    expect(input).toHaveLength(0)
  })
})

describe('detectRegression', () => {
  it('returns null on empty history', () => {
    expect(detectRegression([])).toBeNull()
  })

  it('returns null while warming up (< 25 runs)', () => {
    const h = manyRuns(Array(20).fill(100))
    expect(detectRegression(h)).toBeNull()
  })

  it('returns null when recent is stable vs baseline', () => {
    // 25 runs, all 100ms — no regression
    const h = manyRuns(Array(25).fill(100))
    expect(detectRegression(h)).toBeNull()
  })

  it('returns null when baseline median is below MIN_BASELINE_MS', () => {
    // 20 baseline at 10ms, 5 recent at 100ms (10x ratio but baseline too small to be meaningful)
    const h = manyRuns([...Array(20).fill(10), ...Array(5).fill(100)])
    expect(detectRegression(h)).toBeNull()
  })

  it('fires when recent is materially slower than baseline', () => {
    // 20 baseline at 100ms, 5 recent at 200ms (2x ratio over 1.3 threshold)
    const h = manyRuns([...Array(20).fill(100), ...Array(5).fill(200)])
    const reg = detectRegression(h)
    expect(reg).not.toBeNull()
    expect(reg!.oldMed).toBe(100)
    expect(reg!.newMed).toBe(200)
    expect(reg!.ratio).toBe(2)
  })

  it('does not fire when recent is just below threshold', () => {
    // 1.29x ratio — should not trigger
    const h = manyRuns([...Array(20).fill(100), ...Array(5).fill(129)])
    expect(detectRegression(h)).toBeNull()
  })

  it('fires right at threshold', () => {
    const h = manyRuns([...Array(20).fill(100), ...Array(5).fill(130)])
    const reg = detectRegression(h)
    expect(reg).not.toBeNull()
    expect(reg!.ratio).toBe(1.3)
  })

  it('uses only the 20 runs immediately preceding the recent 5 for baseline', () => {
    // 30 runs total: oldest 5 are very slow (irrelevant), next 20 baseline at 100ms, last 5 at 200ms.
    // If we wrongly included the oldest, baseline would skew.
    const h = manyRuns([...Array(5).fill(1000), ...Array(20).fill(100), ...Array(5).fill(200)])
    const reg = detectRegression(h)
    expect(reg).not.toBeNull()
    expect(reg!.oldMed).toBe(100)
  })

  it('ignores phases content, compares totals only', () => {
    const baseline = Array.from({ length: 20 }, () => run(100, { phases: { a: 50, b: 50 } }))
    const recent = Array.from({ length: 5 }, () => run(200, { phases: { a: 100, b: 100 } }))
    const reg = detectRegression([...baseline, ...recent])
    expect(reg).not.toBeNull()
  })
})
