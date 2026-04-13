/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type ExtensionSets,
  getExtensionIds,
  getOptionalFamilies,
  getRequiredFamilies,
  isDefaultPicked,
  isRequired,
  resolveVariables,
  shellEscape
} from '../../src/core/config'

describe('shellEscape', () => {
  it('wraps a simple string in single quotes', () => {
    expect(shellEscape('hello')).toBe("'hello'")
  })

  it('escapes embedded single quotes', () => {
    expect(shellEscape("it's")).toBe("'it'\\''s'")
  })

  it('handles empty string', () => {
    expect(shellEscape('')).toBe("''")
  })

  it('preserves special shell chars inside single quotes', () => {
    expect(shellEscape('$HOME `cmd` \\n')).toBe("'$HOME `cmd` \\n'")
  })

  it('handles multiple single quotes', () => {
    expect(shellEscape("a'b'c")).toBe("'a'\\''b'\\''c'")
  })
})

const FIXTURE: ExtensionSets = {
  python: {
    extensions: ['ms-python.python', 'ms-python.vscode-pylance'],
    required: true
  },
  frontend: {
    extensions: ['vue.volar'],
    required: false,
    defaultPicked: true
  },
  bazel: ['bazelbuild.vscode-bazel'],
  rust: {
    extensions: ['rust-lang.rust-analyzer'],
    defaultPicked: false
  }
}

describe('getExtensionIds', () => {
  it('returns extensions from ExtensionFamilyConfig', () => {
    expect(getExtensionIds(FIXTURE, 'python')).toEqual([
      'ms-python.python',
      'ms-python.vscode-pylance'
    ])
  })

  it('returns array directly for array entries', () => {
    expect(getExtensionIds(FIXTURE, 'bazel')).toEqual(['bazelbuild.vscode-bazel'])
  })

  it('returns empty array for missing entry', () => {
    expect(getExtensionIds(FIXTURE, 'nonexistent')).toEqual([])
  })
})

describe('isRequired', () => {
  it('returns true for required families', () => {
    expect(isRequired(FIXTURE, 'python')).toBe(true)
  })

  it('returns false for optional families', () => {
    expect(isRequired(FIXTURE, 'frontend')).toBe(false)
  })

  it('returns false for array entries', () => {
    expect(isRequired(FIXTURE, 'bazel')).toBe(false)
  })
})

describe('getRequiredFamilies', () => {
  it('returns only required family names', () => {
    expect(getRequiredFamilies(FIXTURE)).toEqual(['python'])
  })
})

describe('getOptionalFamilies', () => {
  it('returns only optional family names', () => {
    expect(getOptionalFamilies(FIXTURE)).toEqual(['frontend', 'bazel', 'rust'])
  })
})

describe('isDefaultPicked', () => {
  it('returns true for array entries', () => {
    expect(isDefaultPicked(FIXTURE, 'bazel')).toBe(true)
  })

  it('returns true when defaultPicked is true', () => {
    expect(isDefaultPicked(FIXTURE, 'frontend')).toBe(true)
  })

  it('returns true when defaultPicked is not set (defaults to true)', () => {
    expect(isDefaultPicked(FIXTURE, 'python')).toBe(true)
  })

  it('returns false when defaultPicked is explicitly false', () => {
    expect(isDefaultPicked(FIXTURE, 'rust')).toBe(false)
  })
})

// getDisableSettings now reads from settings config via loadConfig — tested via integration

describe('resolveVariables', () => {
  it('replaces ${workspaceFolder} in strings', () => {
    expect(resolveVariables('${workspaceFolder}/src')).toBe('/mock/workspace/src')
  })

  it('replaces ${HOME} in strings', () => {
    const result = resolveVariables('${HOME}/.config')
    expect(result).toMatch(/^\/.+\/\.config$/)
    expect(result).not.toContain('${HOME}')
  })

  it('replaces multiple variables in one string', () => {
    const result = resolveVariables('${workspaceFolder}/foo/${workspaceFolder}/bar')
    expect(result).toBe('/mock/workspace/foo//mock/workspace/bar')
  })

  it('recurses into arrays', () => {
    expect(resolveVariables(['${workspaceFolder}/a', 'plain'])).toEqual([
      '/mock/workspace/a',
      'plain'
    ])
  })

  it('recurses into objects', () => {
    expect(resolveVariables({ path: '${workspaceFolder}/lib', count: 42 })).toEqual({
      path: '/mock/workspace/lib',
      count: 42
    })
  })

  it('passes through numbers unchanged', () => {
    expect(resolveVariables(42)).toBe(42)
  })

  it('passes through booleans unchanged', () => {
    expect(resolveVariables(true)).toBe(true)
  })

  it('passes through null unchanged', () => {
    expect(resolveVariables(null)).toBe(null)
  })
})
