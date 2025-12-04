/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { VerifyCodeResponse } from './twoFactorAuth'
import { type WebAuthnMessage, login, register } from './webauthn'

function getCurrentPageUrl(): string {
  const pathname = window.location.pathname
  const path = pathname.startsWith('/') ? pathname : `/${pathname}`
  return path
}

export async function verifyCode(
  code: string,
  mode: 'totp_credentials' | 'backup_codes',
  originTarget: string = 'index.py'
): Promise<VerifyCodeResponse> {
  const params = new URLSearchParams()
  params.append(mode === 'totp_credentials' ? '_totp_code' : '_backup_code', code)
  params.append('_origtarget', originTarget)

  const response = await fetch(getCurrentPageUrl(), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: params.toString()
  })

  if (!response.ok) {
    throw new Error(
      `Invalid ${mode === 'totp_credentials' ? 'authenticator code' : 'backup code'}. Please try again.`
    )
  }

  return await response.json()
}

export function registerWebAuthn(): Promise<WebAuthnMessage> {
  return register()
}

export function completeWebAuthnLogin(): Promise<WebAuthnMessage> {
  return login()
}
