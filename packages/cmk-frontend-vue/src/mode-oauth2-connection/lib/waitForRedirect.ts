/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export function waitForRedirect<T>(
  win: WindowProxy,
  resolve: (value: T | PromiseLike<T>) => void,
  callback: (win: WindowProxy, resolve: (value: T | PromiseLike<T>) => void) => void
) {
  if (win.location.host === location.host) {
    callback(win, resolve)
  } else {
    setTimeout(() => waitForRedirect(win, resolve, callback), 1000)
  }
}
