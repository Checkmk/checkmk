/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type AuthConfig,
  type CollectorSnippetInput,
  type ExporterConfig,
  buildCollectorSnippets
} from '@/mode-otel/otel-configuration-steps/otelSnippets'

const authOn: AuthConfig = { method: 'basicauth', credential: null }
const authOff: AuthConfig = { method: 'none', credential: null }

const httpConfig: ExporterConfig = {
  endpoint: { address: '172.18.134.39', port: 4318 },
  tlsEnabled: true,
  auth: authOn
}

const baseState: CollectorSnippetInput = {
  siteName: 'mysite',
  httpInfo: httpConfig,
  grpcInfo: null,
  sendLogsToEc: false
}

describe('buildCollectorSnippets', () => {
  it('substitutes endpoint address and port into the exporters snippet', () => {
    const { exporters } = buildCollectorSnippets(baseState)
    expect(exporters).toContain('endpoint: 172.18.134.39:4318')
  })

  it('falls back to placeholders when endpoint is empty', () => {
    const { exporters } = buildCollectorSnippets({
      ...baseState,
      httpInfo: { ...httpConfig, endpoint: { address: '', port: undefined } }
    })
    expect(exporters).not.toContain('endpoint: ')
  })

  describe('TLS block', () => {
    it('renders insecure:false with server_name_override and ca_pem when tlsEnabled is true', () => {
      const { exporters } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, tlsEnabled: true }
      })
      expect(exporters).toContain('tls:')
      expect(exporters).toContain('insecure: false')
      expect(exporters).toContain('server_name_override: "mysite"')
      expect(exporters).toContain('ca_pem: |')
    })

    it('renders insecure:true and omits server_name_override when tlsEnabled is false', () => {
      const { exporters } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, tlsEnabled: false }
      })
      expect(exporters).toContain('insecure: true')
      expect(exporters).not.toContain('server_name_override')
      expect(exporters).not.toContain('ca_pem: |')
    })

    it('falls back to %SITENAME% placeholder when siteName is empty', () => {
      const { exporters } = buildCollectorSnippets({ ...baseState, siteName: '' })
      expect(exporters).toContain('server_name_override: "%SITENAME%"')
    })
  })

  describe('basic auth', () => {
    it('uses basicauth/http for http and basicauth/grpc for grpc in exporters and service', () => {
      const { exporters, extensions, service } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, auth: authOn },
        grpcInfo: { ...httpConfig, auth: authOn }
      })
      expect(exporters).toContain('authenticator: basicauth/http')
      expect(exporters).toContain('authenticator: basicauth/grpc')
      expect(extensions).toContain('basicauth/http:')
      expect(extensions).toContain('basicauth/grpc:')
      expect(service).toContain('extensions: [..., basicauth/http, basicauth/grpc]')
    })

    it('uses placeholder credentials when credential is null', () => {
      const { extensions } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, auth: authOn }
      })
      expect(extensions).toContain('username: {user-name}')
      expect(extensions).toContain('password: {password}')
    })

    it('uses actual credentials when credential is populated', () => {
      const authWithCreds: AuthConfig = {
        method: 'basicauth',
        credential: { username: 'bb', password: 'id_b' }
      }
      const { extensions } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, auth: authWithCreds }
      })
      expect(extensions).toContain('username: bb')
      expect(extensions).toContain('password: id_b')
    })

    it('renders only basicauth/http when only http has auth', () => {
      const { exporters, extensions, service } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, auth: authOn },
        grpcInfo: { ...httpConfig, auth: authOff }
      })
      expect(exporters).toContain('authenticator: basicauth/http')
      expect(exporters).not.toContain('basicauth/grpc')
      expect(extensions).toContain('basicauth/http:')
      expect(extensions).not.toContain('basicauth/grpc:')
      expect(service).toContain('extensions: [..., basicauth/http]')
    })

    it('renders only basicauth/grpc when only grpc has auth', () => {
      const { exporters, extensions, service } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, auth: authOff },
        grpcInfo: { ...httpConfig, auth: authOn }
      })
      expect(exporters).toContain('authenticator: basicauth/grpc')
      expect(exporters).not.toContain('basicauth/http')
      expect(extensions).toContain('basicauth/grpc:')
      expect(extensions).not.toContain('basicauth/http:')
      expect(service).toContain('extensions: [..., basicauth/grpc]')
    })

    it('returns null extensions and drops the service line when auth is disabled', () => {
      const { exporters, extensions, service } = buildCollectorSnippets({
        ...baseState,
        httpInfo: { ...httpConfig, auth: authOff }
      })
      expect(exporters).not.toContain('authenticator:')
      expect(extensions).toBeNull()
      expect(service).not.toContain('basicauth')
    })
  })

  describe('service block', () => {
    it('always renders with the metrics pipeline', () => {
      for (const sendLogsToEc of [true, false]) {
        const { service } = buildCollectorSnippets({ ...baseState, sendLogsToEc })
        expect(service).toContain('service:')
        expect(service).toContain('metrics:')
      }
    })

    it('includes only otlphttp/checkmk when only http is configured', () => {
      const { service } = buildCollectorSnippets({ ...baseState, grpcInfo: null })
      expect(service).toContain('exporters: [..., otlphttp/checkmk]')
      expect(service).not.toContain('otlp/checkmk]')
    })

    it('includes only otlp/checkmk when only grpc is configured', () => {
      const { service } = buildCollectorSnippets({
        ...baseState,
        httpInfo: null,
        grpcInfo: httpConfig
      })
      expect(service).toContain('exporters: [..., otlp/checkmk]')
      expect(service).not.toContain('otlphttp/checkmk')
    })

    it('includes both protocols when both are configured', () => {
      const { service } = buildCollectorSnippets({ ...baseState, grpcInfo: httpConfig })
      expect(service).toContain('exporters: [..., otlphttp/checkmk, otlp/checkmk]')
    })

    it('includes the logs pipeline only when sendLogsToEc is true', () => {
      const off = buildCollectorSnippets({ ...baseState, sendLogsToEc: false })
      expect(off.service).not.toContain('logs:')

      const on = buildCollectorSnippets({ ...baseState, sendLogsToEc: true })
      expect(on.service).toContain('logs:')
    })

    it('uses the same protocol list in the logs pipeline as in metrics', () => {
      const { service } = buildCollectorSnippets({
        ...baseState,
        grpcInfo: httpConfig,
        sendLogsToEc: true
      })
      const metricsExporters = 'exporters: [..., otlphttp/checkmk, otlp/checkmk]'
      // both the metrics and logs pipelines should list the same exporters
      expect(service.split(metricsExporters).length - 1).toBe(2)
    })
  })

  describe('exporter combinations', () => {
    it('renders only the http exporter when grpcInfo is null', () => {
      const { exporters } = buildCollectorSnippets({
        ...baseState,
        httpInfo: httpConfig,
        grpcInfo: null
      })
      expect(exporters).toContain('otlphttp/checkmk:')
    })

    it('renders only the grpc exporter when httpInfo is null', () => {
      const { exporters } = buildCollectorSnippets({
        ...baseState,
        httpInfo: null,
        grpcInfo: httpConfig
      })
      expect(exporters).toContain('otlp/checkmk:')
      expect(exporters).not.toContain('otlphttp/checkmk:')
    })

    it('renders both exporters when both httpInfo and grpcInfo are provided', () => {
      const { exporters } = buildCollectorSnippets({
        ...baseState,
        httpInfo: httpConfig,
        grpcInfo: httpConfig
      })
      expect(exporters).toContain('otlphttp/checkmk:')
      expect(exporters).toContain('otlp/checkmk:')
    })

    it('renders only the placeholder body when both are null', () => {
      const { exporters } = buildCollectorSnippets({
        ...baseState,
        httpInfo: null,
        grpcInfo: null
      })
      expect(exporters).toContain('exporters:')
      expect(exporters).toContain('....')
      expect(exporters).not.toContain('otlp/checkmk:')
      expect(exporters).not.toContain('otlphttp/checkmk:')
    })
  })

  it('produces a minimal snippet when auth, tls, and logs are disabled', () => {
    const { exporters, extensions, service } = buildCollectorSnippets({
      ...baseState,
      httpInfo: { ...httpConfig, tlsEnabled: false, auth: authOff },
      sendLogsToEc: false
    })
    expect(exporters).not.toContain('basicauth')
    expect(exporters).toContain('insecure: true')
    expect(extensions).toBeNull()
    expect(service).not.toContain('extensions:')
    expect(service).not.toContain('logs:')
    expect(service).toContain('metrics:')
  })

  it('produces the full Cloud-style snippet when everything is enabled', () => {
    const { exporters, extensions, service } = buildCollectorSnippets({
      ...baseState,
      httpInfo: { ...httpConfig, tlsEnabled: true, auth: authOn },
      sendLogsToEc: true
    })
    expect(exporters).toContain('insecure: false')
    expect(exporters).toContain('authenticator: basicauth/http')
    expect(extensions).toContain('basicauth/http:')
    expect(service).toContain('extensions: [..., basicauth/http]')
    expect(service).toContain('metrics:')
    expect(service).toContain('logs:')
  })
})
