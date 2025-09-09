/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

interface UseTimer {
  start: () => void
  stop: () => void
  setRefreshInterval: (milliseconds: number) => void
}

/**
 * Utility to handle periodic function calls.
 * @param callback - function to call in regular intervals
 * @param interval - milliseconds between calls. By default, 60 seconds
 * @returns UseTimer
 */
const useTimer = (callback: CallableFunction, interval?: number): UseTimer => {
  let _interval: number = interval || 60_000
  let _timer: number | null = null

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

  return {
    start,
    stop,
    setRefreshInterval
  }
}

export default useTimer
