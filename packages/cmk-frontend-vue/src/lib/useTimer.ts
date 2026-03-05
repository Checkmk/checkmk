/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

interface UseTimer {
  start: () => void
  stop: () => void
  setRefreshInterval: (milliseconds: number) => void
  reportFailure: () => void
  reportSuccess: () => void
}

const BASE_BACKOFF_MS = 10_000
const MAX_BACKOFF_MS = 120_000

/**
 * Utility to handle periodic function calls.
 * @param callback - function to call in regular intervals
 * @param interval - milliseconds between calls. By default, 60 seconds
 * @returns UseTimer
 */
const useTimer = (callback: CallableFunction, interval?: number): UseTimer => {
  let _interval: number = interval || 60_000
  let _timer: number | null = null
  let _consecutiveFailures: number = 0
  let _backoffTimer: number | null = null

  const start = (): void => {
    if (!_timer) {
      _timer = setInterval(callback, _interval)
    }
  }

  const stop = (): void => {
    if (_timer) {
      clearInterval(_timer)
      _timer = null
    }
    if (_backoffTimer) {
      clearTimeout(_backoffTimer)
      _backoffTimer = null
    }
  }

  const setRefreshInterval = (milliseconds: number): void => {
    const isRunning = _timer !== null
    if (isRunning) {
      stop()
    }
    _interval = milliseconds
    if (isRunning) {
      start()
    }
  }

  const reportFailure = (): void => {
    _consecutiveFailures++
    const backoff =
      _interval + Math.min(BASE_BACKOFF_MS * Math.pow(2, _consecutiveFailures - 1), MAX_BACKOFF_MS)
    // Stop normal polling and schedule a delayed restart
    if (_timer) {
      clearInterval(_timer)
      _timer = null
    }
    if (_backoffTimer) {
      clearTimeout(_backoffTimer)
    }
    _backoffTimer = window.setTimeout(() => {
      _backoffTimer = null
      callback()
      start()
    }, backoff)
  }

  const reportSuccess = (): void => {
    _consecutiveFailures = 0
    if (_backoffTimer) {
      clearTimeout(_backoffTimer)
      _backoffTimer = null
    }
    // Ensure normal polling is running
    if (!_timer) {
      start()
    }
  }

  return {
    start,
    stop,
    setRefreshInterval,
    reportFailure,
    reportSuccess
  }
}

export default useTimer
