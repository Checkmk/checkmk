/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { isValidIpOrHostname } from '@/mode-otel/otel-configuration-steps/validation'

describe('isValidIpOrHostname', () => {
  describe('IPv4', () => {
    it.each(['0.0.0.0', '127.0.0.1', '192.168.1.1', '255.255.255.255'])(
      'accepts valid address %s',
      (addr) => expect(isValidIpOrHostname(addr)).toBe(true)
    )
    it.each(['256.0.0.1', '999.999.999.999', '1.2.3'])('rejects invalid address %s', (addr) =>
      expect(isValidIpOrHostname(addr)).toBe(false)
    )
  })

  describe('IPv6', () => {
    it.each([
      '2001:db8::1',
      '::1',
      '::',
      'fe80::1',
      '2001:db8:85a3::8a2e:370:7334',
      '1:2:3:4:5:6:7:8'
    ])('accepts valid address %s', (addr) => expect(isValidIpOrHostname(addr)).toBe(true))

    it.each([
      ['triple colon', ':::'],
      ['multiple :: expansions', '1::2::3'],
      ['too many groups with ::', '::1:2:3:4:5:6:7:8'],
      ['trailing colon without ::', '1:2:3:4:5:6:7:']
    ])('rejects %s (%s)', (_desc, addr) => expect(isValidIpOrHostname(addr)).toBe(false))
  })

  describe('hostname', () => {
    it.each(['example.com', 'foo.bar.baz', 'my-host', 'localhost'])(
      'accepts valid hostname %s',
      (h) => expect(isValidIpOrHostname(h)).toBe(true)
    )
    it.each(['-invalid.com', 'invalid-.com', `${'a'.repeat(64)}.com`])(
      'rejects invalid hostname %s',
      (h) => expect(isValidIpOrHostname(h)).toBe(false)
    )
  })
})
