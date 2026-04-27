/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import * as cmkFetch from '@/lib/cmkFetch'

import ConfigureCollector from '@/mode-otel/otel-configuration-steps/ConfigureCollector.vue'
import type {
  AuthConfig,
  EndpointConfig,
  EventConsoleConfig
} from '@/mode-otel/otel-configuration-steps/otelTypes'
import type { PasswordConfig } from '@/mode-otel/otel-configuration-steps/password_store_password.types.ts'

function mockPasswordsResponse(passwords: { id: string; title: string }[] = []) {
  return vi.spyOn(cmkFetch, 'fetchRestAPI').mockResolvedValue({
    raiseForStatus: vi.fn().mockResolvedValue(undefined),
    json: vi.fn().mockResolvedValue({ value: passwords })
  } as unknown as cmkFetch.CmkFetchResponse)
}

function mockPasswordsError() {
  vi.spyOn(cmkFetch, 'fetchRestAPI').mockRejectedValue(new Error('Network error'))
}

function renderComponent(
  noAuthAllowed = true,
  endpointConfigAllowed = true,
  encryptionAllowed = true,
  eventConsoleAllowed = true,
  grpcDefaultPort = 4317,
  httpDefaultPort = 4318,
  initialGrpcEnabled = true,
  initialHttpEnabled = false
) {
  const grpcEnabled = ref<boolean>(initialGrpcEnabled)
  const httpEnabled = ref<boolean>(initialHttpEnabled)
  const grpcAuth = ref<AuthConfig>({
    method: noAuthAllowed ? 'none' : 'basicauth',
    credential: null
  })
  const httpAuth = ref<AuthConfig>({
    method: noAuthAllowed ? 'none' : 'basicauth',
    credential: null
  })
  const grpcEndpoint = ref<EndpointConfig>({
    socketAddressType: 'custom',
    address: '0.0.0.0',
    port: 4317
  })
  const httpEndpoint = ref<EndpointConfig>({
    socketAddressType: 'custom',
    address: '0.0.0.0',
    port: 4318
  })
  const grpcEncryption = ref<boolean>(false)
  const httpEncryption = ref<boolean>(false)
  const grpcEventConsole = ref<EventConsoleConfig | null>(null)
  const httpEventConsole = ref<EventConsoleConfig | null>(null)
  const pendingPasswords = ref<Map<string, PasswordConfig>>(new Map())
  const compRef = ref<InstanceType<typeof ConfigureCollector>>()

  render(
    defineComponent({
      components: { ConfigureCollector },
      setup: () => ({
        grpcEnabled,
        httpEnabled,
        grpcAuth,
        httpAuth,
        grpcEndpoint,
        httpEndpoint,
        grpcEncryption,
        httpEncryption,
        grpcEventConsole,
        httpEventConsole,
        pendingPasswords,
        compRef,
        noAuthAllowed,
        endpointConfigAllowed,
        encryptionAllowed,
        eventConsoleAllowed,
        grpcDefaultPort,
        httpDefaultPort
      }),
      template: `<ConfigureCollector ref="compRef" :no-auth-allowed="noAuthAllowed" :endpoint-config-allowed="endpointConfigAllowed" :encryption-allowed="encryptionAllowed" :event-console-allowed="eventConsoleAllowed" :grpc-default-port="grpcDefaultPort" :http-default-port="httpDefaultPort" v-model:grpc-enabled="grpcEnabled" v-model:http-enabled="httpEnabled" v-model:grpc-auth="grpcAuth" v-model:http-auth="httpAuth" v-model:grpc-endpoint="grpcEndpoint" v-model:http-endpoint="httpEndpoint" v-model:grpc-encryption="grpcEncryption" v-model:http-encryption="httpEncryption" v-model:grpc-event-console="grpcEventConsole" v-model:http-event-console="httpEventConsole" v-model:pending-passwords="pendingPasswords" />`
    })
  )

  return {
    grpcEnabled,
    httpEnabled,
    grpcAuth,
    httpAuth,
    grpcEndpoint,
    httpEndpoint,
    grpcEncryption,
    httpEncryption,
    grpcEventConsole,
    httpEventConsole,
    pendingPasswords,
    compRef
  }
}

describe('ConfigureCollector', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  describe('default auth method', () => {
    test('defaults to "none" when no-auth is allowed', async () => {
      mockPasswordsResponse()
      const { grpcAuth, httpAuth } = renderComponent(true)

      expect(grpcAuth.value.method).toBe('none')
      expect(httpAuth.value.method).toBe('none')
    })

    test('defaults to "basicauth" when no-auth is not allowed', async () => {
      mockPasswordsResponse()
      const { grpcAuth, httpAuth } = renderComponent(false)

      expect(grpcAuth.value.method).toBe('basicauth')
      expect(httpAuth.value.method).toBe('basicauth')
    })
  })

  describe('auth method options', () => {
    test('shows "No authentication" option when no-auth is allowed', async () => {
      mockPasswordsResponse()
      renderComponent(true)

      // The GRPC tab is active by default; auth dropdown should be rendered
      await waitFor(() => {
        expect(screen.getByText('Authentication method')).toBeInTheDocument()
      })
    })

    test('hides "No authentication" option when no-auth is not allowed', async () => {
      mockPasswordsResponse()
      renderComponent(false)

      await waitFor(() => {
        expect(screen.getByText('Authentication method')).toBeInTheDocument()
      })
      // "No authentication" should not appear as an option
      expect(screen.queryByText('No authentication')).not.toBeInTheDocument()
    })
  })

  describe('credential fields visibility', () => {
    test('credential fields do not appear when method is "none"', async () => {
      mockPasswordsResponse()
      renderComponent(true)

      await waitFor(() => {
        expect(screen.queryByText('Username')).not.toBeInTheDocument()
      })
    })

    test('credential fields appear when basicauth is selected', async () => {
      mockPasswordsResponse()
      renderComponent(false)

      await waitFor(() => {
        expect(screen.getByText('Username')).toBeInTheDocument()
      })
    })
  })

  describe('validation', () => {
    test('validate() returns true for "none" auth method', async () => {
      mockPasswordsResponse()
      const { compRef } = renderComponent(true)

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns false if credential has empty username', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      const { compRef, grpcAuth } = renderComponent(true)

      grpcAuth.value.method = 'basicauth'
      grpcAuth.value.credential = { username: '', password: 'pw1' }

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('Username is required but not specified.')
    })

    test('validate() returns false if credential has no password', async () => {
      mockPasswordsResponse()
      const { compRef, grpcAuth } = renderComponent(true)

      grpcAuth.value.method = 'basicauth'
      grpcAuth.value.credential = { username: 'admin', password: '' }

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('Password is required but not specified.')
    })

    test('validate() returns true for valid basicauth credential with TLS enabled', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      const { compRef, grpcAuth, grpcEncryption } = renderComponent(true)

      grpcAuth.value.method = 'basicauth'
      grpcAuth.value.credential = { username: 'admin', password: 'pw1' }
      grpcEncryption.value = true

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns false if only HTTP tab has invalid credential', async () => {
      mockPasswordsError()
      const { compRef, httpAuth, httpEnabled } = renderComponent(true)

      httpEnabled.value = true
      httpAuth.value.method = 'basicauth'
      httpAuth.value.credential = { username: '', password: '' }

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
    })
  })

  describe('TLS validation', () => {
    test('validate() returns false when basicauth is selected without TLS', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      const { compRef, grpcAuth, grpcEncryption } = renderComponent(true)

      grpcAuth.value.method = 'basicauth'
      grpcAuth.value.credential = { username: 'admin', password: 'pw1' }
      grpcEncryption.value = false

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('TLS encryption must be enabled when using basic authentication.')
    })

    test('validate() returns true when basicauth with TLS enabled', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      const { compRef, grpcAuth, grpcEncryption } = renderComponent(true)

      grpcAuth.value.method = 'basicauth'
      grpcAuth.value.credential = { username: 'admin', password: 'pw1' }
      grpcEncryption.value = true

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() skips TLS check when encryptionAllowed=false', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      const { compRef, grpcAuth } = renderComponent(true, true, false)

      grpcAuth.value.method = 'basicauth'
      grpcAuth.value.credential = { username: 'admin', password: 'pw1' }

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns false when only HTTP tab has basicauth without TLS', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      const { compRef, httpAuth, httpEncryption, httpEnabled } = renderComponent(true)

      httpEnabled.value = true
      httpAuth.value.method = 'basicauth'
      httpAuth.value.credential = { username: 'admin', password: 'pw1' }
      httpEncryption.value = false

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
    })
  })

  describe('encryption field visibility', () => {
    test('encryption checkbox is shown when encryptionAllowed=true', async () => {
      mockPasswordsResponse()
      renderComponent(true, true, true)

      await waitFor(() => {
        expect(screen.getByText('Encrypt communication with TLS')).toBeInTheDocument()
      })
    })

    test('encryption checkbox is absent when encryptionAllowed=false', async () => {
      mockPasswordsResponse()
      renderComponent(true, true, false)

      await waitFor(() => {
        expect(screen.queryByText('Encrypt communication with TLS')).not.toBeInTheDocument()
      })
    })
  })

  describe('event console field visibility', () => {
    test('event console checkbox is shown when eventConsoleAllowed=true', async () => {
      mockPasswordsResponse()
      renderComponent(true, true, true, true)

      await waitFor(() => {
        expect(screen.getByText('Send log messages to event console')).toBeInTheDocument()
      })
    })

    test('event console checkbox is absent when eventConsoleAllowed=false', async () => {
      mockPasswordsResponse()
      renderComponent(true, true, true, false)

      await waitFor(() => {
        expect(screen.queryByText('Send log messages to event console')).not.toBeInTheDocument()
      })
    })
  })

  describe('event console sub-field', () => {
    test('resource attribute field is hidden when event console is disabled', async () => {
      mockPasswordsResponse()
      renderComponent(true, true, true, true)

      await waitFor(() => {
        expect(
          screen.queryByText('Resource attribute for host name lookup')
        ).not.toBeInTheDocument()
      })
    })

    test('resource attribute field appears when event console is enabled', async () => {
      mockPasswordsResponse()
      const { grpcEventConsole } = renderComponent(true, true, true, true)

      grpcEventConsole.value = { resourceAttribute: '' }

      await waitFor(() => {
        expect(screen.getByText('Resource attribute for host name lookup')).toBeInTheDocument()
        expect(screen.getByPlaceholderText('service.name')).toBeInTheDocument()
      })
    })
  })

  describe('event console validation', () => {
    test('validate() returns false when event console enabled with empty resource attribute', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEventConsole } = renderComponent(true, true, true, true)

      grpcEventConsole.value = { resourceAttribute: '' }

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText(
        'You must set a resource attribute (e.g., service.name) so the system can determine the host name.'
      )
    })

    test('validate() returns true when event console enabled with non-empty resource attribute', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEventConsole } = renderComponent(true, true, true, true)

      grpcEventConsole.value = { resourceAttribute: 'service.name' }

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns true when event console is disabled (null)', async () => {
      mockPasswordsResponse()
      const { compRef } = renderComponent(true, true, true, true)

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })
  })

  describe('endpoint fields visibility', () => {
    test('IP/port fields are shown when endpointConfigAllowed=true', async () => {
      mockPasswordsResponse()
      renderComponent(true, true)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('0.0.0.0')).toBeInTheDocument()
      })
    })

    test('IP/port fields are absent when endpointConfigAllowed=false', async () => {
      mockPasswordsResponse()
      renderComponent(true, false)

      await waitFor(() => {
        expect(screen.queryByPlaceholderText('0.0.0.0')).not.toBeInTheDocument()
      })
    })
  })

  describe('endpoint validation', () => {
    test('validate() returns true for valid address and port', async () => {
      mockPasswordsResponse()
      const { compRef } = renderComponent(true, true)

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns true when only GRPC address is set and HTTP is empty', async () => {
      mockPasswordsResponse()
      const { compRef, httpEndpoint } = renderComponent(true, true)

      httpEndpoint.value.address = ''
      httpEndpoint.value.port = undefined

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns true when only HTTP address is set and GRPC is empty', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint } = renderComponent(true, true)

      grpcEndpoint.value.address = ''
      grpcEndpoint.value.port = undefined

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns false when both addresses are empty', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint, httpEndpoint } = renderComponent(true, true)

      grpcEndpoint.value.address = ''
      httpEndpoint.value.address = ''

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('Enter a valid IP address or host name.')
    })

    test('shows both address and port errors together when both endpoints are unconfigured', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint, httpEndpoint } = renderComponent(true, true)

      grpcEndpoint.value.address = ''
      grpcEndpoint.value.port = undefined
      httpEndpoint.value.address = ''
      httpEndpoint.value.port = undefined

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      compRef.value!.validate()

      const addressErrors = await screen.findAllByText('Enter a valid IP address or host name.')
      const portErrors = await screen.findAllByText('Enter a valid port number (example: 1234).')
      expect(addressErrors.length).toBeGreaterThan(0)
      expect(portErrors.length).toBeGreaterThan(0)
    })

    test('validate() returns false when HTTP address is invalid', async () => {
      mockPasswordsResponse()
      const { compRef, httpEndpoint, httpEnabled } = renderComponent(true, true)

      httpEnabled.value = true
      httpEndpoint.value.address = 'not..valid'

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
    })

    test('validate() returns false when HTTP has port but no address', async () => {
      mockPasswordsResponse()
      const { compRef, httpEndpoint, httpEnabled } = renderComponent(true, true)

      httpEnabled.value = true
      httpEndpoint.value.address = ''
      httpEndpoint.value.port = 4318

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('Enter a valid IP address or host name.')
    })

    test('validate() returns false when GRPC has port but no address', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint } = renderComponent(true, true)

      grpcEndpoint.value.address = ''
      grpcEndpoint.value.port = 4317

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('Enter a valid IP address or host name.')
    })

    test('validate() returns false when configured GRPC endpoint has undefined port', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint } = renderComponent(true, true)

      grpcEndpoint.value.port = undefined

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
    })

    test('validate() returns false when gRPC and HTTP use the same port', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint, httpEndpoint, httpEnabled } = renderComponent(true, true)

      httpEnabled.value = true
      grpcEndpoint.value.port = 4317
      httpEndpoint.value.port = 4317

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('Port must differ from the other protocol endpoint.')
    })

    test('validate() returns true when gRPC and HTTP use different ports', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint, httpEndpoint } = renderComponent(true, true)

      grpcEndpoint.value.port = 4317
      httpEndpoint.value.port = 4318

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns true when endpointConfigAllowed=false regardless of endpoint values', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEndpoint } = renderComponent(true, false)

      grpcEndpoint.value.address = ''
      grpcEndpoint.value.port = undefined

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })
  })

  describe('password creation tracking', () => {
    function makePasswordConfig(id: string, title: string): PasswordConfig {
      return {
        general_props: { id, title, comment: '', docu_url: '' },
        password_props: { password: 'secret', owned_by: ['admins', null], share_with: [] }
      }
    }

    test('stores newly created password in the map', async () => {
      mockPasswordsResponse()
      const { compRef, pendingPasswords } = renderComponent(false)

      await waitFor(() => expect(compRef.value).toBeDefined())

      const pw = makePasswordConfig('pw-new-1', 'My New Password')
      compRef.value!.onPasswordCreated(pw)

      expect(pendingPasswords.value.get('pw-new-1')).toEqual(pw)
    })

    test('stores multiple newly created passwords', async () => {
      mockPasswordsResponse()
      const { compRef, pendingPasswords } = renderComponent(false)

      await waitFor(() => expect(compRef.value).toBeDefined())

      compRef.value!.onPasswordCreated(makePasswordConfig('pw-1', 'First'))
      compRef.value!.onPasswordCreated(makePasswordConfig('pw-2', 'Second'))

      expect(pendingPasswords.value.size).toBe(2)
      expect(pendingPasswords.value.has('pw-1')).toBe(true)
      expect(pendingPasswords.value.has('pw-2')).toBe(true)
    })

    test('replaces password when creating with same ID', async () => {
      mockPasswordsResponse()
      const { compRef, pendingPasswords } = renderComponent(false)

      await waitFor(() => expect(compRef.value).toBeDefined())

      compRef.value!.onPasswordCreated(makePasswordConfig('pw-dup', 'Original'))
      compRef.value!.onPasswordCreated(makePasswordConfig('pw-dup', 'Replaced'))

      expect(pendingPasswords.value.size).toBe(1)
      expect(pendingPasswords.value.get('pw-dup')!.general_props.title).toBe('Replaced')
    })

    test('auto-selects newly created password in the triggering tab', async () => {
      mockPasswordsResponse()
      const { compRef, grpcAuth } = renderComponent(false)

      grpcAuth.value.credential = { username: 'admin', password: null }

      await waitFor(() => expect(compRef.value).toBeDefined())

      compRef.value!.onPasswordCreated(makePasswordConfig('pw-auto', 'Auto Selected'))

      expect(grpcAuth.value.credential!.password).toBe('pw-auto')
    })

    test('cross-selects in other tab when it has no password', async () => {
      mockPasswordsResponse()
      const { compRef, grpcAuth, httpAuth } = renderComponent(false)

      grpcAuth.value.credential = { username: 'admin', password: null }
      httpAuth.value.credential = { username: 'admin', password: null }

      await waitFor(() => expect(compRef.value).toBeDefined())

      compRef.value!.onPasswordCreated(makePasswordConfig('pw-cross', 'Cross Selected'))

      expect(grpcAuth.value.credential!.password).toBe('pw-cross')
      expect(httpAuth.value.credential!.password).toBe('pw-cross')
    })

    test('does not cross-select when other tab already has a password', async () => {
      mockPasswordsResponse([{ id: 'existing-pw', title: 'Existing' }])
      const { compRef, grpcAuth, httpAuth } = renderComponent(false)

      grpcAuth.value.credential = { username: 'admin', password: null }
      httpAuth.value.credential = { username: 'admin', password: 'existing-pw' }

      await waitFor(() => expect(compRef.value).toBeDefined())

      compRef.value!.onPasswordCreated(makePasswordConfig('pw-new', 'New Password'))

      expect(grpcAuth.value.credential!.password).toBe('pw-new')
      expect(httpAuth.value.credential!.password).toBe('existing-pw')
    })
  })

  describe('enabled/disabled tab behaviour', () => {
    test('validate() returns false when both tabs are disabled', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEnabled, httpEnabled } = renderComponent(
        true,
        true,
        true,
        true,
        4317,
        4318,
        false,
        false
      )

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(false)
      await screen.findByText('At least one receiver (GRPC or HTTP) must be enabled.')

      // Confirm both are actually disabled
      expect(grpcEnabled.value).toBe(false)
      expect(httpEnabled.value).toBe(false)
    })

    test('validate() returns true when only GRPC is enabled and valid', async () => {
      mockPasswordsResponse()
      const { compRef, httpEnabled } = renderComponent(
        true,
        true,
        true,
        true,
        4317,
        4318,
        true,
        false
      )

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      expect(httpEnabled.value).toBe(false)
      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() returns true when only HTTP is enabled and valid', async () => {
      mockPasswordsResponse()
      const { compRef, grpcEnabled } = renderComponent(
        true,
        true,
        true,
        true,
        4317,
        4318,
        false,
        true
      )

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      expect(grpcEnabled.value).toBe(false)
      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() skips auth validation for a disabled tab', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      // HTTP is disabled (default); give it invalid basicauth — should still pass
      const { compRef, httpAuth, httpEncryption } = renderComponent(true)

      httpAuth.value.method = 'basicauth'
      httpAuth.value.credential = { username: '', password: '' }
      httpEncryption.value = false

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('validate() skips TLS check for a disabled tab', async () => {
      mockPasswordsResponse([{ id: 'pw1', title: 'Password 1' }])
      // HTTP is disabled (default); basicauth without TLS on disabled tab should not fail
      const { compRef, httpAuth, httpEncryption } = renderComponent(true, true, true)

      httpAuth.value.method = 'basicauth'
      httpAuth.value.credential = { username: 'admin', password: 'pw1' }
      httpEncryption.value = false

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })

    test('port conflict is ignored when one tab is disabled', async () => {
      mockPasswordsResponse()
      // HTTP is disabled (default); same port on both endpoints should not trigger conflict
      const { compRef, grpcEndpoint, httpEndpoint } = renderComponent(true, true)

      grpcEndpoint.value.port = 4317
      httpEndpoint.value.port = 4317

      await waitFor(() => expect(compRef.value).toBeDefined())
      await new Promise((r) => setTimeout(r, 0))

      const result = compRef.value!.validate()
      expect(result).toBe(true)
    })
  })
})
