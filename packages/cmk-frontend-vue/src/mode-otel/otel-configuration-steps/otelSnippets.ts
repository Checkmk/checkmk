/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AuthConfig, Credential, EndpointConfig } from './otelTypes'

export type { AuthConfig, Credential }

export interface CollectorSnippetInput {
  siteName: string
  httpInfo: ExporterConfig | null
  grpcInfo: ExporterConfig | null
  sendLogsToEc: boolean
}

export interface CollectorSnippets {
  exporters: string
  extensions: string | null
  service: string
}

export interface ExporterConfig {
  endpoint: EndpointConfig
  tlsEnabled: boolean
  auth: AuthConfig
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
      password: ${password}`
}

export function buildExporter(
  config: ExporterConfig,
  protocol: 'http' | 'grpc',
  siteName: string
): string {
  const address = config.endpoint.address || '<host>'
  const port = config.endpoint.port ?? 4318
  const authenticatorName = protocol === 'http' ? 'basicauth/http' : 'basicauth/grpc'

  const authBlock =
    config.auth.method === 'basicauth'
      ? `
    auth:
      authenticator: ${authenticatorName}`
      : ''

  const tlsBlock = config.tlsEnabled
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

  return `otlp${protocol === 'http' ? 'http' : ''}/checkmk:
    endpoint: ${address}:${port}${authBlock}${tlsBlock}
`
}

export function buildCollectorSnippets(state: CollectorSnippetInput): CollectorSnippets {
  const siteName = state.siteName || '%SITENAME%'

  const exporters = `exporters:
  ....
  ${`${state.httpInfo?.endpoint.address ? buildExporter(state.httpInfo, 'http', siteName) : ''}
  ${state.grpcInfo?.endpoint.address ? buildExporter(state.grpcInfo, 'grpc', siteName) : ''}`.trim()}`

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
    ...(state.httpInfo?.endpoint.address ? ['otlphttp/checkmk'] : []),
    ...(state.grpcInfo?.endpoint.address ? ['otlp/checkmk'] : [])
  ]
  const exportersList =
    activeProtocols.length > 0 ? `[..., ${activeProtocols.join(', ')}]` : '[...]'

  const logsPipeline = state.sendLogsToEc
    ? `
    logs:
      ...
      exporters: ${exportersList}`
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
