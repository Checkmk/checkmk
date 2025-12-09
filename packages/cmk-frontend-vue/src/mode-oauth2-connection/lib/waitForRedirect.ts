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
  if (validateRedirectLocation(win, validate)) {
    callback(win, resolve)
  } else if (win.closed) {
    callback(win, resolve, 'Window was closed before redirect.')
  } else if (timeout && timeout <= 0) {
    callback(win, resolve, 'Timeout.')
  } else {
    setTimeout(
      () => waitForRedirect(win, validate, resolve, callback, timeout ? timeout - 1000 : timeout),
      1000
    )
  }
}

function validateRedirectLocation(win: WindowProxy, validate: IRedirectValidateObject): boolean {
  let valid = false
  for (const key in Object.keys(validate)) {
    switch (key) {
      case 'host':
        if (win.location.host !== validate.host) {
          return false
        } else {
          valid = true
        }
        break
      case 'hostname':
        if (win.location.hostname !== validate.hostname) {
          return false
        } else {
          valid = true
        }
        break
      case 'href':
        if (win.location.href !== validate.href) {
          return false
        } else {
          valid = true
        }
        break
    }
  }

  return valid
}
