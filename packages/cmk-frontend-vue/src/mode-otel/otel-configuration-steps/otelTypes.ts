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

export type SocketAddressType = 'default_ipv4' | 'default_ipv6' | 'custom'

export interface EndpointConfig {
  socketAddressType: SocketAddressType
  address: string
  port: number | undefined
}

export interface EventConsoleConfig {
  resourceAttribute: string
}

export const GRPC_DEFAULT_PORT = 4317
export const HTTP_DEFAULT_PORT = 4318

export interface ResolvedEndpoint {
  address: string
  port: number
}

// Resolves an EndpointConfig into the concrete address/port the collector will
// actually bind to. The "default" socket-address modes leave `address`/`port`
// empty in the form state so the UI inputs stay hidden; consumers that need
// the real values (snippet builders, SDK examples) go through this resolver.
export function resolveEndpoint(cfg: EndpointConfig, defaultPort: number): ResolvedEndpoint | null {
  switch (cfg.socketAddressType) {
    case 'default_ipv4':
      return { address: '0.0.0.0', port: defaultPort }
    case 'default_ipv6':
      return { address: '[::]', port: defaultPort }
    case 'custom': {
      const address = cfg.address.trim()
      if (!address || cfg.port === undefined) {
        return null
      }
      return { address, port: cfg.port }
    }
  }
}
