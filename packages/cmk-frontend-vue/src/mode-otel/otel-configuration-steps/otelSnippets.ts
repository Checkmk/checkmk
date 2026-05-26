/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type AuthConfig,
  type Credential,
  type EndpointConfig,
  GRPC_DEFAULT_PORT,
  HTTP_DEFAULT_PORT,
  resolveEndpoint
} from './otelTypes'

export type { AuthConfig, Credential }

export interface CollectorSnippetInput {
  siteName: string
  httpInfo: ExporterConfig | null
  grpcInfo: ExporterConfig | null
}

export interface CollectorSnippets {
  exporters: string
  extensions: string | null
  service: string
}

export interface ExporterConfig {
  endpoint: EndpointConfig
  tlsEnabled: boolean
  tlsSimple?: boolean
  auth: AuthConfig
  eventConsole: boolean
  overrideEndpoint?: string
}

function buildAuthExtension(auth: AuthConfig, name: string): string | null {
  if (auth.method !== 'basicauth') {
    return null
  }
  const username = auth.credential?.username ?? '{user-name}'
  const password = auth.credential?.password ?? '{password}'
  return `  ${name}:
    client_auth:
      username: ${username}
      password: <REPLACE_ME> # Use the value of ${password}`
}

export function buildExporter(
  config: ExporterConfig,
  protocol: 'http' | 'grpc',
  siteName: string
): string {
  const defaultPort = protocol === 'http' ? HTTP_DEFAULT_PORT : GRPC_DEFAULT_PORT
  const authenticatorName = protocol === 'http' ? 'basicauth/http' : 'basicauth/grpc'

  let endpointStr: string
  if (config.overrideEndpoint !== undefined) {
    endpointStr = config.overrideEndpoint
  } else {
    const resolved = resolveEndpoint(config.endpoint, defaultPort)
    const isDefaultSocket =
      config.endpoint.socketAddressType === 'default_ipv4' ||
      config.endpoint.socketAddressType === 'default_ipv6'
    const address = isDefaultSocket ? '<REPLACE_ME>' : (resolved?.address ?? '<host>')
    const port = resolved?.port ?? defaultPort
    const endpointComment = isDefaultSocket ? " # address of the Checkmk site's server" : ''
    endpointStr = `${address}:${port}${endpointComment}`
  }

  const authBlock =
    config.auth.method === 'basicauth'
      ? `
    auth:
      authenticator: ${authenticatorName}`
      : ''

  let tlsBlock: string
  if (config.tlsSimple) {
    tlsBlock = `
    tls:
      insecure: ${config.tlsEnabled ? 'false' : 'true'}`
  } else {
    tlsBlock = config.tlsEnabled
      ? `
    tls:
      insecure: false
      server_name_override: "${siteName}"
      ca_pem: |
      ----BEGIN CERTIFICATE-----
      YOUR SITE CA # Public part of ~/etc/ssl/ca.pem
      ----END CERTIFICATE-----
      `
      : `
    tls:
      insecure: true`
  }

  return `otlp${protocol === 'http' ? 'http' : ''}/checkmk:
    endpoint: ${endpointStr}${authBlock}${tlsBlock}
`
}

export function buildCollectorSnippets(state: CollectorSnippetInput): CollectorSnippets {
  const siteName = state.siteName || '%SITENAME%'

  const httpResolved = state.httpInfo
    ? resolveEndpoint(state.httpInfo.endpoint, HTTP_DEFAULT_PORT)
    : null
  const grpcResolved = state.grpcInfo
    ? resolveEndpoint(state.grpcInfo.endpoint, GRPC_DEFAULT_PORT)
    : null

  const exporters = `exporters:
  ....
  ${`${httpResolved && state.httpInfo ? buildExporter(state.httpInfo, 'http', siteName) : ''}
  ${grpcResolved && state.grpcInfo ? buildExporter(state.grpcInfo, 'grpc', siteName) : ''}`.trim()}`

  const httpAuthEntry = state.httpInfo
    ? buildAuthExtension(state.httpInfo.auth, 'basicauth/http')
    : null
  const grpcAuthEntry = state.grpcInfo
    ? buildAuthExtension(state.grpcInfo.auth, 'basicauth/grpc')
    : null
  const authEntries = [httpAuthEntry, grpcAuthEntry].filter((e): e is string => e !== null)

  const extensions =
    authEntries.length > 0 ? `extensions:\n  ....\n${authEntries.join('\n')}\n` : null

  const activeAuthNames = [
    ...(httpAuthEntry ? ['basicauth/http'] : []),
    ...(grpcAuthEntry ? ['basicauth/grpc'] : [])
  ]
  const serviceExtensionsLine =
    activeAuthNames.length > 0 ? `extensions: [..., ${activeAuthNames.join(', ')}]` : ''

  const activeProtocols = [
    ...(httpResolved ? ['otlphttp/checkmk'] : []),
    ...(grpcResolved ? ['otlp/checkmk'] : [])
  ]
  const exportersList =
    activeProtocols.length > 0 ? `[..., ${activeProtocols.join(', ')}]` : '[...]'

  const logs = [
    ...(state.httpInfo?.eventConsole ? ['otlphttp/checkmk'] : []),
    ...(state.grpcInfo?.eventConsole ? ['otlp/checkmk'] : [])
  ]

  const logsExportersList = logs.length > 0 ? `[..., ${logs.join(', ')}]` : '[...]'

  const logsPipeline =
    logs.length > 0
      ? `
    logs:
      ...
      exporters: ${logsExportersList}`
      : ''

  const service = `service:
  ...
  ${serviceExtensionsLine}
  ...
  pipelines:
    metrics:
      ...
      exporters: ${exportersList}${logsPipeline}
  ...
`

  return { exporters, extensions, service }
}
