/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type EndpointConfig,
  GRPC_DEFAULT_PORT,
  HTTP_DEFAULT_PORT,
  resolveEndpoint
} from '@/mode-otel/otel-configuration-steps/otelTypes'

describe('resolveEndpoint', () => {
  it('returns 0.0.0.0 with the supplied default port for default_ipv4', () => {
    const cfg: EndpointConfig = { socketAddressType: 'default_ipv4', address: '', port: undefined }
    expect(resolveEndpoint(cfg, HTTP_DEFAULT_PORT)).toEqual({
      address: '0.0.0.0',
      port: HTTP_DEFAULT_PORT
    })
  })

  it('returns [::] with the supplied default port for default_ipv6', () => {
    const cfg: EndpointConfig = { socketAddressType: 'default_ipv6', address: '', port: undefined }
    expect(resolveEndpoint(cfg, GRPC_DEFAULT_PORT)).toEqual({
      address: '[::]',
      port: GRPC_DEFAULT_PORT
    })
  })

  it('ignores stale address/port fields when in a default mode', () => {
    const cfg: EndpointConfig = {
      socketAddressType: 'default_ipv4',
      address: 'leftover-from-custom',
      port: 9999
    }
    expect(resolveEndpoint(cfg, HTTP_DEFAULT_PORT)).toEqual({
      address: '0.0.0.0',
      port: HTTP_DEFAULT_PORT
    })
  })

  it('returns the user-typed values for custom mode', () => {
    const cfg: EndpointConfig = {
      socketAddressType: 'custom',
      address: '172.18.134.39',
      port: 4321
    }
    expect(resolveEndpoint(cfg, HTTP_DEFAULT_PORT)).toEqual({
      address: '172.18.134.39',
      port: 4321
    })
  })

  it('trims surrounding whitespace from the custom address', () => {
    const cfg: EndpointConfig = {
      socketAddressType: 'custom',
      address: '  10.0.0.1  ',
      port: 4318
    }
    expect(resolveEndpoint(cfg, HTTP_DEFAULT_PORT)).toEqual({
      address: '10.0.0.1',
      port: 4318
    })
  })

  it('returns null for custom mode when the address is blank', () => {
    const cfg: EndpointConfig = { socketAddressType: 'custom', address: '   ', port: 4318 }
    expect(resolveEndpoint(cfg, HTTP_DEFAULT_PORT)).toBeNull()
  })

  it('returns null for custom mode when the port is undefined', () => {
    const cfg: EndpointConfig = {
      socketAddressType: 'custom',
      address: '10.0.0.1',
      port: undefined
    }
    expect(resolveEndpoint(cfg, HTTP_DEFAULT_PORT)).toBeNull()
  })
})
