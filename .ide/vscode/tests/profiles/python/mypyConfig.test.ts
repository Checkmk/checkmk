/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { parseVersion, versionAtLeast } from '../../../src/core/version'
import { buildMypyIniContent } from '../../../src/profiles/python/mypyConfig'

describe('parseVersion', () => {
  it('parses three-part version', () => {
    expect(parseVersion('1.20.3')).toEqual({ major: 1, minor: 20, patch: 3 })
  })

  it('parses two-part version (patch defaults to 0)', () => {
    expect(parseVersion('1.20')).toEqual({ major: 1, minor: 20, patch: 0 })
  })

  it('parses single-part version', () => {
    expect(parseVersion('2')).toEqual({ major: 2, minor: 0, patch: 0 })
  })
})

describe('versionAtLeast', () => {
  it('returns true when versions are equal', () => {
    expect(versionAtLeast('1.20.0', '1.20.0')).toBe(true)
  })

  it('returns true when major is greater', () => {
    expect(versionAtLeast('2.0.0', '1.20.0')).toBe(true)
  })

  it('returns true when minor is greater', () => {
    expect(versionAtLeast('1.21.0', '1.20.0')).toBe(true)
  })

  it('returns true when patch is greater', () => {
    expect(versionAtLeast('1.20.1', '1.20.0')).toBe(true)
  })

  it('returns false when major is less', () => {
    expect(versionAtLeast('0.20.0', '1.20.0')).toBe(false)
  })

  it('returns false when minor is less', () => {
    expect(versionAtLeast('1.19.0', '1.20.0')).toBe(false)
  })

  it('returns false when patch is less', () => {
    expect(versionAtLeast('1.20.0', '1.20.1')).toBe(false)
  })

  it('handles two-part versions', () => {
    expect(versionAtLeast('1.20', '1.20')).toBe(true)
    expect(versionAtLeast('1.19', '1.20')).toBe(false)
  })
})

describe('buildMypyIniContent', () => {
  it('generates [mypy] header with version comment', () => {
    const result = buildMypyIniContent('1.20.0', {})
    expect(result).toContain('[mypy]')
    expect(result).toContain('Mypy version: 1.20.0')
    expect(result).toContain('AUTO-GENERATED')
  })

  it('includes boolean options', () => {
    const result = buildMypyIniContent('1.20.0', { strict: true, warn_return_any: false })
    expect(result).toContain('strict = true')
    expect(result).toContain('warn_return_any = false')
  })

  it('includes string options', () => {
    const result = buildMypyIniContent('1.20.0', { python_version: '3.12' })
    expect(result).toContain('python_version = 3.12')
  })

  it('cleans mypy_path by removing $MYPY_CONFIG_FILE_DIR/', () => {
    const result = buildMypyIniContent('1.20.0', {
      mypy_path: '$MYPY_CONFIG_FILE_DIR/stubs:$MYPY_CONFIG_FILE_DIR/lib'
    })
    expect(result).toContain('mypy_path = stubs:lib')
  })

  it('forces follow_imports to normal', () => {
    const result = buildMypyIniContent('1.20.0', { follow_imports: 'skip' })
    expect(result).toContain('follow_imports = normal')
  })

  it('omits version-gated options for old mypy', () => {
    const result = buildMypyIniContent('1.19.0', { strict_bytes: true })
    expect(result).toContain('# strict_bytes = true')
    expect(result).toContain('requires mypy >= 1.20')
  })

  it('includes version-gated options for new mypy', () => {
    const result = buildMypyIniContent('1.20.0', { strict_bytes: true })
    expect(result).toContain('strict_bytes = true')
    expect(result).not.toContain('# strict_bytes')
  })

  it('filters version-gated error codes', () => {
    const result = buildMypyIniContent('1.19.0', {
      enable_error_code: ['return', 'deprecated', 'exhaustive-match']
    })
    expect(result).toContain('enable_error_code = return')
    expect(result).toContain('# enable_error_code: deprecated (requires >= 1.20)')
    expect(result).toContain('# enable_error_code: exhaustive-match (requires >= 1.20)')
  })

  it('includes all error codes when version is sufficient', () => {
    const result = buildMypyIniContent('1.20.0', {
      enable_error_code: ['return', 'deprecated', 'exhaustive-match']
    })
    expect(result).toContain('enable_error_code = return, deprecated, exhaustive-match')
  })

  it('generates override sections per module', () => {
    const result = buildMypyIniContent('1.20.0', {
      overrides: [
        {
          module: ['tests.*', 'testlib.*'],
          disallow_untyped_defs: false
        }
      ]
    })
    expect(result).toContain('[mypy-tests.*]')
    expect(result).toContain('[mypy-testlib.*]')
    expect(result).toContain('disallow_untyped_defs = false')
  })
})
