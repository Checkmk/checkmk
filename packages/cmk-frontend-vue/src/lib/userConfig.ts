/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type UserFrontendConfig } from 'cmk-shared-typing/typescript/user_frontend_config'

import { fetchRestAPI } from './cmkFetch'
import { CmkSimpleError } from './error'

const CONFIG_COOKIE = 'user_frontend_config'

export function getUserFrontendConfig(): UserFrontendConfig | null {
  const cookieValue = _getCookie(CONFIG_COOKIE)

  if (cookieValue === null) {
    return null
  }

  try {
    return JSON.parse(cookieValue)
  } catch {
    throw new CmkSimpleError('Failed to parse user frontend config cookie')
  }
}

export function isWarningDismissed(warning: string, deflt: boolean): boolean {
  const config = getUserFrontendConfig()
  if (config === null || !config.dismissed_warnings) {
    return deflt
  }
  return config.dismissed_warnings.includes(warning)
}

// Notifies the server to record the dismissal. The server updates the
// user_frontend_config cookie, which isWarningDismissed reads on next load.
export async function persistWarningDismissal(warning: string) {
  await fetchRestAPI('api/1.0/domain-types/user_config/actions/dismiss-warning/invoke', 'POST', {
    warning: warning
  })
}

function _getCookie(cookieName: string): string | null {
  if (document.cookie.length === 0) {
    return null
  }

  let cookieStart = document.cookie.indexOf(`${cookieName}=`)
  if (cookieStart === -1) {
    return null
  }

  cookieStart = cookieStart + cookieName.length + 1
  let cookieEnd = document.cookie.indexOf(';', cookieStart)
  if (cookieEnd === -1) {
    cookieEnd = document.cookie.length
  }

  return decodeURIComponent(document.cookie.substring(cookieStart, cookieEnd))
}
