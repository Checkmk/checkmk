/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { hasValidRelayNameCharacters } from '@/mode-relay/lib/validation'

describe('hasValidRelayNameCharacters', () => {
  test('should accept valid relay names with Unicode letters', () => {
    expect(hasValidRelayNameCharacters('MyRelay')).toBe(true)
    expect(hasValidRelayNameCharacters('Relay_123')).toBe(true)
    expect(hasValidRelayNameCharacters('Test Relay')).toBe(true)
    expect(hasValidRelayNameCharacters('relay$name')).toBe(true)
    expect(hasValidRelayNameCharacters('relay-name')).toBe(true)
    expect(hasValidRelayNameCharacters('relay@domain')).toBe(true)
    expect(hasValidRelayNameCharacters('relay.name')).toBe(true)
    expect(hasValidRelayNameCharacters('relay+name')).toBe(true)
    expect(hasValidRelayNameCharacters('Relay123')).toBe(true)
    expect(hasValidRelayNameCharacters('_relay')).toBe(true)
    expect(hasValidRelayNameCharacters('123relay')).toBe(true)
  })

  test('should accept Unicode characters', () => {
    expect(hasValidRelayNameCharacters('Relé')).toBe(true)
    expect(hasValidRelayNameCharacters('测试Relay')).toBe(true)
    expect(hasValidRelayNameCharacters('Ρελέ')).toBe(true)
    expect(hasValidRelayNameCharacters('Reläy123')).toBe(true)
  })

  test('should reject invalid characters', () => {
    expect(hasValidRelayNameCharacters('relay#name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay%name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay&name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay*name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay(name)')).toBe(false)
    expect(hasValidRelayNameCharacters('relay[name]')).toBe(false)
    expect(hasValidRelayNameCharacters('relay{name}')).toBe(false)
    expect(hasValidRelayNameCharacters('relay\\name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay/name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay|name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay<name>')).toBe(false)
    expect(hasValidRelayNameCharacters('relay>name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay?name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay:name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay;name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay"name"')).toBe(false)
    expect(hasValidRelayNameCharacters("relay'name'")).toBe(false)
    expect(hasValidRelayNameCharacters('relay=name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay!name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay~name')).toBe(false)
    expect(hasValidRelayNameCharacters('relay`name`')).toBe(false)
  })

  test('should reject names that start with invalid characters', () => {
    expect(hasValidRelayNameCharacters('#relay')).toBe(false)
    expect(hasValidRelayNameCharacters('!relay')).toBe(false)
    expect(hasValidRelayNameCharacters('@relay')).toBe(false) // @ is only allowed after first character
    expect(hasValidRelayNameCharacters('.relay')).toBe(false) // . is only allowed after first character
    expect(hasValidRelayNameCharacters('+relay')).toBe(false) // + is only allowed after first character
    expect(hasValidRelayNameCharacters('-relay')).toBe(false) // - is only allowed after first character
  })

  test('should handle edge cases', () => {
    expect(hasValidRelayNameCharacters('')).toBe(false)
    expect(hasValidRelayNameCharacters(' ')).toBe(false) // single space is not valid
    expect(hasValidRelayNameCharacters('a')).toBe(true) // single character
    expect(hasValidRelayNameCharacters('1')).toBe(true) // single digit
    expect(hasValidRelayNameCharacters('_')).toBe(true) // single underscore
    expect(hasValidRelayNameCharacters('$')).toBe(true) // single dollar sign
    expect(hasValidRelayNameCharacters('end-with-hyphen-')).toBe(true) // trailing hyphen is allowed
  })

  test('should work with complex valid names', () => {
    expect(hasValidRelayNameCharacters('Production_Relay-2023@company.com+backup')).toBe(true)
    expect(hasValidRelayNameCharacters('Test Relay_123$backup-version.2+final')).toBe(true)
    expect(hasValidRelayNameCharacters('üñíçødé_relay_123')).toBe(true)
  })
})
