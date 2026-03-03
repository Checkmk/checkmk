/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export const OAUTH2_REDIRECT_MESSAGE_TYPE = 'oauth2-redirect'

export function waitForRedirect<T>(
  win: WindowProxy,
  resolve: (value: T | PromiseLike<T>) => void,
  callback: (
    win: WindowProxy,
    resolve: (value: T | PromiseLike<T>) => void,
    error?: string,
    redirectHref?: string
  ) => void,
  timeout?: number
) {
  function onMessage(event: MessageEvent) {
    if (event.source !== win) {
      return
    }
    if (event.origin !== location.origin) {
      return
    }
    if (event.data?.type !== OAUTH2_REDIRECT_MESSAGE_TYPE) {
      return
    }
    cleanup(timeoutHandle, closedPollHandle, onMessage)
    callback(win, resolve, undefined, event.data.href)
  }

  let timeoutHandle: ReturnType<typeof setTimeout> | null = null
  window.addEventListener('message', onMessage)

  const closedPollHandle = setInterval(() => {
    try {
      if (win.closed) {
        cleanup(timeoutHandle, closedPollHandle, onMessage)
        callback(win, resolve, 'Window was closed before redirect.')
      }
    } catch {
      // COOP policy may block win.closed on cross-origin windows
    }
  }, 500)

  if (timeout !== undefined) {
    timeoutHandle = setTimeout(() => {
      cleanup(timeoutHandle, closedPollHandle, onMessage)
      callback(win, resolve, 'Authorization timed out. Please try again.')
    }, timeout)
  }
}

function cleanup(
  timeoutHandle: ReturnType<typeof setTimeout> | null,
  closedPollHandle: ReturnType<typeof setInterval>,
  onMessage: (event: MessageEvent) => void
) {
  if (timeoutHandle) {
    clearTimeout(timeoutHandle)
  }
  clearInterval(closedPollHandle)
  window.removeEventListener('message', onMessage)
}
