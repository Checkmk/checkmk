/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen } from '@testing-library/vue'

import OTelConfigurationSummary from '@/mode-otel/otel-configuration-steps/OTelConfigurationSummary.vue'
import type {
  AuthConfig,
  EndpointConfig,
  EventConsoleConfig
} from '@/mode-otel/otel-configuration-steps/otelTypes'

const DEFAULT_ENDPOINT: EndpointConfig = {
  socketAddressType: 'default_ipv4',
  address: '',
  port: undefined
}

const NONE_AUTH: AuthConfig = { method: 'none', credential: null }

function basicAuth(username: string, passwordId: string): AuthConfig {
  return {
    method: 'basicauth',
    credential: { username, password: passwordId }
  }
}

interface RenderProps {
  configName?: string
  siteId?: string
  grpcEnabled?: boolean
  httpEnabled?: boolean
  grpcAuth?: AuthConfig
  httpAuth?: AuthConfig
  grpcEndpoint?: EndpointConfig
  httpEndpoint?: EndpointConfig
  grpcEncryption?: boolean
  httpEncryption?: boolean
  grpcEventConsole?: EventConsoleConfig | null
  httpEventConsole?: EventConsoleConfig | null
  grpcPasswordIsNew?: boolean
  httpPasswordIsNew?: boolean
  endpointConfigAllowed?: boolean
  encryptionAllowed?: boolean
  eventConsoleAllowed?: boolean
}

function renderSummary(props: RenderProps = {}) {
  const merged = {
    configName: 'otel_cfg_1',
    siteId: 'mysite',
    grpcEnabled: true,
    httpEnabled: false,
    grpcAuth: NONE_AUTH,
    httpAuth: NONE_AUTH,
    grpcEndpoint: DEFAULT_ENDPOINT,
    httpEndpoint: DEFAULT_ENDPOINT,
    grpcEncryption: false,
    httpEncryption: false,
    grpcEventConsole: null,
    httpEventConsole: null,
    grpcPasswordIsNew: false,
    httpPasswordIsNew: false,
    endpointConfigAllowed: true,
    encryptionAllowed: true,
    eventConsoleAllowed: true,
    ...props
  }
  render(OTelConfigurationSummary, { props: merged })
}

describe('OTelConfigurationSummary', () => {
  afterEach(() => {
    cleanup()
  })

  describe('protocol selection', () => {
    test('gRPC-only renders only the gRPC section', () => {
      renderSummary({ grpcEnabled: true, httpEnabled: false })

      expect(screen.getByText(/gRPC protocol/)).toBeInTheDocument()
      expect(screen.queryByText(/HTTP protocol/)).toBeNull()
    })

    test('HTTP-only renders only the HTTP section', () => {
      renderSummary({ grpcEnabled: false, httpEnabled: true })

      expect(screen.getByText(/HTTP protocol/)).toBeInTheDocument()
      expect(screen.queryByText(/gRPC protocol/)).toBeNull()
    })

    test('both enabled renders gRPC before HTTP', () => {
      renderSummary({ grpcEnabled: true, httpEnabled: true })

      const grpcHeading = screen.getByText(/gRPC protocol/)
      const httpHeading = screen.getByText(/HTTP protocol/)
      expect(grpcHeading).toBeInTheDocument()
      expect(httpHeading).toBeInTheDocument()
      // gRPC comes before HTTP in the DOM order.
      expect(
        grpcHeading.compareDocumentPosition(httpHeading) & Node.DOCUMENT_POSITION_FOLLOWING
      ).not.toBe(0)
    })

    test('renders neither section when both are disabled', () => {
      renderSummary({ grpcEnabled: false, httpEnabled: false })

      expect(screen.queryByText(/gRPC protocol/)).toBeNull()
      expect(screen.queryByText(/HTTP protocol/)).toBeNull()
      // General fields still render.
      expect(screen.getByText(/Configuration name/)).toBeInTheDocument()
    })
  })

  describe('authentication rendering', () => {
    test("'none' auth renders 'No authentication' and no username", () => {
      renderSummary({ grpcEnabled: true, grpcAuth: NONE_AUTH })

      expect(screen.getByText(/No authentication/)).toBeInTheDocument()
      expect(screen.queryByText(/Basic auth/)).toBeNull()
    })

    test("'basicauth' with passwordIsNew=true renders 'newly created' marker", () => {
      renderSummary({
        grpcEnabled: true,
        grpcAuth: basicAuth('alice', 'quick_setup_password_1'),
        grpcPasswordIsNew: true
      })

      expect(screen.getByText(/Basic auth.*alice.*newly created/)).toBeInTheDocument()
      // Never leak the password-store ID.
      expect(screen.queryByText(/quick_setup_password_/)).toBeNull()
    })

    test("'basicauth' with passwordIsNew=false renders 'existing' marker", () => {
      renderSummary({
        grpcEnabled: true,
        grpcAuth: basicAuth('alice', 'some_existing_id'),
        grpcPasswordIsNew: false
      })

      expect(screen.getByText(/Basic auth.*alice.*existing/)).toBeInTheDocument()
      expect(screen.queryByText(/some_existing_id/)).toBeNull()
    })
  })

  describe('endpoint resolution', () => {
    test('default_ipv4 on gRPC resolves to 0.0.0.0:4317', () => {
      renderSummary({
        grpcEnabled: true,
        grpcEndpoint: { socketAddressType: 'default_ipv4', address: '', port: undefined }
      })

      expect(screen.getByText(/0\.0\.0\.0:4317/)).toBeInTheDocument()
    })

    test('default_ipv4 on HTTP resolves to 0.0.0.0:4318', () => {
      renderSummary({
        grpcEnabled: false,
        httpEnabled: true,
        httpEndpoint: { socketAddressType: 'default_ipv4', address: '', port: undefined }
      })

      expect(screen.getByText(/0\.0\.0\.0:4318/)).toBeInTheDocument()
    })

    test('default_ipv6 on gRPC resolves to [::]:4317', () => {
      renderSummary({
        grpcEnabled: true,
        grpcEndpoint: { socketAddressType: 'default_ipv6', address: '', port: undefined }
      })

      expect(screen.getByText(/\[::\]:4317/)).toBeInTheDocument()
    })

    test('custom address renders the user-supplied values', () => {
      renderSummary({
        grpcEnabled: true,
        grpcEndpoint: { socketAddressType: 'custom', address: '127.0.0.1', port: 5555 }
      })

      expect(screen.getByText(/127\.0\.0\.1:5555/)).toBeInTheDocument()
    })
  })

  describe('edition gating', () => {
    test('endpointConfigAllowed=false suppresses the endpoint row', () => {
      renderSummary({ grpcEnabled: true, endpointConfigAllowed: false })

      expect(screen.queryByText(/Endpoint/)).toBeNull()
      expect(screen.queryByText(/0\.0\.0\.0:4317/)).toBeNull()
    })

    test('encryptionAllowed=false suppresses the encryption row', () => {
      renderSummary({ grpcEnabled: true, encryptionAllowed: false, grpcEncryption: true })

      // Heading 'Encryption:' must not be present
      expect(screen.queryByText(/^Encryption:$/)).toBeNull()
      expect(screen.queryByText(/TLS enabled/)).toBeNull()
    })

    test('eventConsoleAllowed=false suppresses the event-console row even when configured', () => {
      renderSummary({
        grpcEnabled: true,
        eventConsoleAllowed: false,
        grpcEventConsole: { resourceAttribute: 'service.name' }
      })

      expect(screen.queryByText(/Event Console/)).toBeNull()
      expect(screen.queryByText(/service\.name/)).toBeNull()
    })
  })

  describe('encryption row', () => {
    test('renders TLS enabled when encryption=true', () => {
      renderSummary({ grpcEnabled: true, grpcEncryption: true })

      expect(screen.getByText(/TLS enabled/)).toBeInTheDocument()
    })

    test('renders No encryption when encryption=false', () => {
      renderSummary({ grpcEnabled: true, grpcEncryption: false })

      expect(screen.getByText(/No encryption/)).toBeInTheDocument()
    })
  })

  describe('event console row', () => {
    test('absent when eventConsole=null', () => {
      renderSummary({ grpcEnabled: true, grpcEventConsole: null })

      expect(screen.queryByText(/Event Console/)).toBeNull()
    })

    test('renders the resource attribute when eventConsole is set', () => {
      renderSummary({
        grpcEnabled: true,
        grpcEventConsole: { resourceAttribute: 'service.name' }
      })

      expect(screen.getByText(/Event Console/)).toBeInTheDocument()
      expect(screen.getByText(/service\.name/)).toBeInTheDocument()
    })
  })

  test('renders general configuration name and site rows', () => {
    renderSummary({ configName: 'my_otel', siteId: 'mysite' })

    expect(screen.getByText(/my_otel/)).toBeInTheDocument()
    expect(screen.getByText(/mysite/)).toBeInTheDocument()
  })

  test('renders the Telemetry folder footnote', () => {
    renderSummary()

    expect(screen.getByText(/hosts will be created/)).toBeInTheDocument()
  })
})
