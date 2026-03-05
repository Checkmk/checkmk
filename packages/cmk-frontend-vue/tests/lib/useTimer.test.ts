/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import useTimer from '@/lib/useTimer'

describe('useTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('calls callback at regular intervals', () => {
    const cb = vi.fn()
    const timer = useTimer(cb, 1000)
    timer.start()

    vi.advanceTimersByTime(3000)
    expect(cb).toHaveBeenCalledTimes(3)

    timer.stop()
  })

  it('does not call callback after stop', () => {
    const cb = vi.fn()
    const timer = useTimer(cb, 1000)
    timer.start()
    vi.advanceTimersByTime(1000)
    expect(cb).toHaveBeenCalledTimes(1)

    timer.stop()
    vi.advanceTimersByTime(5000)
    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('changes interval with setRefreshInterval', () => {
    const cb = vi.fn()
    const timer = useTimer(cb, 1000)
    timer.start()

    timer.setRefreshInterval(500)
    vi.advanceTimersByTime(2000)
    expect(cb).toHaveBeenCalledTimes(4)

    timer.stop()
  })

  describe('backoff on failure', () => {
    // With interval=1000ms, backoff = 1000 + min(10000 * 2^(n-1), 120000)
    // 1st failure: 1000 + 10000 = 11s
    // 2nd failure: 1000 + 20000 = 21s
    // 3rd failure: 1000 + 40000 = 41s

    it('stops normal polling and schedules retry after first failure', () => {
      const cb = vi.fn()
      const timer = useTimer(cb, 1000)
      timer.start()

      vi.advanceTimersByTime(1000)
      expect(cb).toHaveBeenCalledTimes(1)

      timer.reportFailure()

      // Normal interval calls should not happen during backoff
      vi.advanceTimersByTime(10_000)
      expect(cb).toHaveBeenCalledTimes(1)

      // First backoff is 1s + 10s = 11s
      vi.advanceTimersByTime(1_000)
      expect(cb).toHaveBeenCalledTimes(2)

      timer.stop()
    })

    it('doubles backoff on consecutive failures', () => {
      const cb = vi.fn()
      const timer = useTimer(cb, 1000)
      timer.start()

      // First failure: 1s + 10s = 11s backoff
      timer.reportFailure()
      vi.advanceTimersByTime(11_000)
      expect(cb).toHaveBeenCalledTimes(1)

      // Second failure: 1s + 20s = 21s backoff
      timer.reportFailure()
      vi.advanceTimersByTime(20_000)
      expect(cb).toHaveBeenCalledTimes(1) // not yet
      vi.advanceTimersByTime(1_000)
      expect(cb).toHaveBeenCalledTimes(2) // retry after 21s

      // Third failure: 1s + 40s = 41s backoff
      timer.reportFailure()
      vi.advanceTimersByTime(40_000)
      expect(cb).toHaveBeenCalledTimes(2) // not yet
      vi.advanceTimersByTime(1_000)
      expect(cb).toHaveBeenCalledTimes(3) // retry after 41s

      timer.stop()
    })

    it('caps backoff at 120 seconds plus interval', () => {
      const cb = vi.fn()
      const timer = useTimer(cb, 1000)
      timer.start()

      // Simulate many failures to exceed cap
      for (let i = 0; i < 5; i++) {
        timer.reportFailure()
      }

      // 5th failure: 1000 + min(10000 * 2^4, 120000) = 1000 + 120000 = 121s
      vi.advanceTimersByTime(120_000)
      expect(cb).toHaveBeenCalledTimes(0)
      vi.advanceTimersByTime(1_000)
      expect(cb).toHaveBeenCalledTimes(1)

      timer.stop()
    })

    it('includes configured interval in backoff delay', () => {
      const cb = vi.fn()
      // 30s interval: backoff = 30s + 10s = 40s
      const timer = useTimer(cb, 30_000)
      timer.start()

      timer.reportFailure()

      vi.advanceTimersByTime(10_000)
      expect(cb).toHaveBeenCalledTimes(0) // not at 10s
      vi.advanceTimersByTime(20_000)
      expect(cb).toHaveBeenCalledTimes(0) // not at 30s
      vi.advanceTimersByTime(10_000)
      expect(cb).toHaveBeenCalledTimes(1) // fires at 40s

      timer.stop()
    })

    it('resets backoff on success and resumes normal polling', () => {
      const cb = vi.fn()
      const timer = useTimer(cb, 1000)
      timer.start()

      timer.reportFailure()
      // During backoff, report success
      timer.reportSuccess()

      // Normal polling should resume
      vi.advanceTimersByTime(3000)
      expect(cb).toHaveBeenCalledTimes(3)

      timer.stop()
    })

    it('resets failure counter on success', () => {
      const cb = vi.fn()
      const timer = useTimer(cb, 1000)
      timer.start()

      // Accumulate failures
      timer.reportFailure()
      timer.reportFailure()
      timer.reportFailure()

      // Success resets
      timer.reportSuccess()

      // New failure should start at 1s + 10s = 11s again (not 1s + 80s)
      timer.reportFailure()
      vi.advanceTimersByTime(11_000)
      expect(cb).toHaveBeenCalledTimes(1)

      timer.stop()
    })

    it('stop clears backoff timer', () => {
      const cb = vi.fn()
      const timer = useTimer(cb, 1000)
      timer.start()

      timer.reportFailure()
      timer.stop()

      vi.advanceTimersByTime(30_000)
      expect(cb).toHaveBeenCalledTimes(0)
    })
  })
})
