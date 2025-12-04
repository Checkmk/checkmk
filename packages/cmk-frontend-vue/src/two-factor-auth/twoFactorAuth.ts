/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export type AuthMode =
  | 'totp_credentials'
  | 'webauthn_credentials'
  | 'backup_codes'
  | 'multipleEnabled'

export interface VerifyCodeResponse {
  status: 'OK' | 'ERROR'
  redirect?: string
  replicate?: boolean
}
