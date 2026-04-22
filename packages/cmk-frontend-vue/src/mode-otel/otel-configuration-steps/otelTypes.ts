/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export type AuthMethod = 'none' | 'basicauth'

export interface Credential {
  username: string
  password: string | null // password store ID
}

export interface AuthConfig {
  method: AuthMethod
  credential: Credential | null
}

export interface EndpointConfig {
  address: string
  port: number | undefined
}

export interface EventConsoleConfig {
  resourceAttribute: string
}
