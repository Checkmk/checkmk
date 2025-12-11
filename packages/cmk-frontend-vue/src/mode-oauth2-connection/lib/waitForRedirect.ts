/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface IRedirectValidateObject {
  host?: string
  href?: string
  hostname?: string
}

export function waitForRedirect<T>(
  win: WindowProxy,
  validate: IRedirectValidateObject,
  resolve: (value: T | PromiseLike<T>) => void,
  callback: (
    win: WindowProxy,
    resolve: (value: T | PromiseLike<T>) => void,
    error?: string
  ) => void,
  timeout?: number
) {
  let valid = false
  try {
    for (const key of Object.keys(validate)) {
      switch (key) {
        case 'host':
          valid = win.location.host === validate.host
          break
        case 'hostname':
          valid = win.location.hostname === validate.hostname
          break
        case 'href':
          valid = win.location.href === validate.href
          break
      }
    }
  } catch {
    // not allowed to access the location, so no redirect happend
  }

  if (valid) {
    callback(win, resolve)
  } else if (win.window === null) {
    callback(win, resolve, 'Window was closed before redirect.')
  } else if (timeout && timeout <= 0) {
    callback(win, resolve, 'Timeout.')
  } else {
    setTimeout(() => {
      waitForRedirect(win, validate, resolve, callback, timeout ? timeout - 1000 : timeout)
    }, 1000)
  }
}
