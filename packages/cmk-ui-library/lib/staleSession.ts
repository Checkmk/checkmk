/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'

type SessionResponse = Pick<Response, 'status' | 'redirected' | 'url'>

type ReportScope = Window & { [StaleSession.REPORTED_KEY]?: true }

export class StaleSessionError extends CmkApiError {
  constructor(url: string) {
    super('Your session has expired. Please log in again.', null, url, 401)
    this.name = 'StaleSessionError'
  }
}

export class StaleSession {
  static readonly REPORTED_KEY = '__cmkStaleSessionReported'

  static isStale(response: SessionResponse): boolean {
    const path = StaleSession.pathOf(response.url)
    if (response.redirected && path.endsWith('/login.py')) {
      return true
    }
    return response.status === 401 && path.includes('/check_mk/api/')
  }

  private static pathOf(url: string): string {
    try {
      return new URL(url, window.location.href).pathname
    } catch {
      return ''
    }
  }

  static check(response: SessionResponse, requestUrl: string): void {
    if (StaleSession.isStale(response)) {
      StaleSession.report()
      throw new StaleSessionError(requestUrl)
    }
  }

  static report(): void {
    const scope = StaleSession.scope()
    if (scope[StaleSession.REPORTED_KEY]) {
      return
    }
    scope[StaleSession.REPORTED_KEY] = true
    console.warn('Checkmk: your session has expired. Please log in again.')
  }

  private static scope(): ReportScope {
    try {
      if (window.top && window.top.location.origin === window.location.origin) {
        return window.top as ReportScope
      }
    } catch {
      return window as ReportScope
    }
    return window as ReportScope
  }
}
