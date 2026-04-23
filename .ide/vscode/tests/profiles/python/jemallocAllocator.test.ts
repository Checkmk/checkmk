/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const originalPlatform = process.platform

function setPlatform(p: NodeJS.Platform): void {
  Object.defineProperty(process, 'platform', { value: p, configurable: true })
}

function restorePlatform(): void {
  Object.defineProperty(process, 'platform', { value: originalPlatform, configurable: true })
}

describe('buildWrapperScript', () => {
  afterEach(restorePlatform)

  it('emits an LD_PRELOAD line preserving any existing value on Linux', async () => {
    setPlatform('linux')
    vi.resetModules()
    const { buildWrapperScript } = await import('../../../src/profiles/python/jemallocAllocator')
    const script = buildWrapperScript(
      '/usr/lib/x86_64-linux-gnu/libjemalloc.so.2',
      '/ws/.venv/bin/dmypy'
    )
    expect(script).toMatch(/^#!\/usr\/bin\/env bash\n/)
    expect(script).toContain(
      'export LD_PRELOAD="${LD_PRELOAD:+$LD_PRELOAD:}/usr/lib/x86_64-linux-gnu/libjemalloc.so.2"'
    )
    expect(script).toContain('export PYTHONMALLOC=malloc')
    expect(script).toContain('exec "/ws/.venv/bin/dmypy" "$@"')
    expect(script).not.toContain('DYLD_INSERT_LIBRARIES')
  })

  it('emits DYLD_INSERT_LIBRARIES + DYLD_FORCE_FLAT_NAMESPACE on macOS', async () => {
    setPlatform('darwin')
    vi.resetModules()
    const { buildWrapperScript } = await import('../../../src/profiles/python/jemallocAllocator')
    const script = buildWrapperScript('/opt/homebrew/lib/libjemalloc.dylib', '/ws/.venv/bin/dmypy')
    expect(script).toContain(
      'export DYLD_INSERT_LIBRARIES="${DYLD_INSERT_LIBRARIES:+$DYLD_INSERT_LIBRARIES:}/opt/homebrew/lib/libjemalloc.dylib"'
    )
    expect(script).toContain('export DYLD_FORCE_FLAT_NAMESPACE=1')
    expect(script).not.toContain('LD_PRELOAD')
  })

  it('escapes double quotes in the dmypy path', async () => {
    setPlatform('linux')
    vi.resetModules()
    const { buildWrapperScript } = await import('../../../src/profiles/python/jemallocAllocator')
    const script = buildWrapperScript('/lib/libjemalloc.so.2', '/ws/"quirky"/dmypy')
    expect(script).toContain('exec "/ws/\\"quirky\\"/dmypy" "$@"')
  })
})

describe('detectJemallocPath', () => {
  beforeEach(() => {
    vi.resetModules()
  })
  afterEach(() => {
    restorePlatform()
    vi.doUnmock('../../../src/core/shell')
    vi.doUnmock('fs')
  })

  it('returns null on unsupported platforms', async () => {
    setPlatform('win32')
    const { detectJemallocPath } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(detectJemallocPath()).toBeNull()
  })

  it('returns null on Linux when ldconfig yields no match', async () => {
    setPlatform('linux')
    vi.doMock('../../../src/core/shell', () => ({ safeExec: () => '' }))
    const { detectJemallocPath } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(detectJemallocPath()).toBeNull()
  })

  it('returns the ldconfig path on Linux when the file exists', async () => {
    setPlatform('linux')
    vi.doMock('../../../src/core/shell', () => ({
      safeExec: () => '/usr/lib/x86_64-linux-gnu/libjemalloc.so.2'
    }))
    vi.doMock('fs', () => ({ existsSync: () => true }))
    const { detectJemallocPath } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(detectJemallocPath()).toBe('/usr/lib/x86_64-linux-gnu/libjemalloc.so.2')
  })

  it('returns null on Linux when ldconfig points at a missing file', async () => {
    setPlatform('linux')
    vi.doMock('../../../src/core/shell', () => ({
      safeExec: () => '/nonexistent/libjemalloc.so.2'
    }))
    vi.doMock('fs', () => ({ existsSync: () => false }))
    const { detectJemallocPath } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(detectJemallocPath()).toBeNull()
  })

  it('returns null on macOS when brew has no jemalloc prefix', async () => {
    setPlatform('darwin')
    vi.doMock('../../../src/core/shell', () => ({ safeExec: () => '' }))
    const { detectJemallocPath } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(detectJemallocPath()).toBeNull()
  })

  it('returns the brew-composed path on macOS when present', async () => {
    setPlatform('darwin')
    vi.doMock('../../../src/core/shell', () => ({
      safeExec: () => '/opt/homebrew/Cellar/jemalloc/5.3.0'
    }))
    vi.doMock('fs', () => ({ existsSync: () => true }))
    const { detectJemallocPath } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(detectJemallocPath()).toBe('/opt/homebrew/Cellar/jemalloc/5.3.0/lib/libjemalloc.dylib')
  })
})

describe('isDefaultDmypyValue', () => {
  const wsFolder = { uri: { fsPath: '/ws' } } as never

  beforeEach(() => {
    vi.resetModules()
  })
  afterEach(() => {
    vi.doUnmock('../../../src/core/config')
  })

  it('returns true for the cmk-ext placeholder form', async () => {
    vi.doMock('../../../src/core/config', () => ({
      resolveVariables: (v: string) => v.replace('${cmk-ext:workspaceFolder}', '/ws')
    }))
    const { isDefaultDmypyValue } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(isDefaultDmypyValue('${cmk-ext:workspaceFolder}/.venv/bin/dmypy', wsFolder)).toBe(true)
  })

  it('returns true for the resolved absolute default', async () => {
    vi.doMock('../../../src/core/config', () => ({ resolveVariables: (v: string) => v }))
    const { isDefaultDmypyValue } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(isDefaultDmypyValue('/ws/.venv/bin/dmypy', wsFolder)).toBe(true)
  })

  it('returns true for the legacy ${workspaceFolder} form (still present in older .code-workspace files)', async () => {
    vi.doMock('../../../src/core/config', () => ({ resolveVariables: (v: string) => v }))
    const { isDefaultDmypyValue } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(isDefaultDmypyValue('${workspaceFolder}/.venv/bin/dmypy', wsFolder)).toBe(true)
  })

  it('returns false for an unrelated custom path', async () => {
    vi.doMock('../../../src/core/config', () => ({ resolveVariables: (v: string) => v }))
    const { isDefaultDmypyValue } = await import('../../../src/profiles/python/jemallocAllocator')
    expect(isDefaultDmypyValue('/opt/custom/dmypy', wsFolder)).toBe(false)
  })
})

describe('installCommandForPlatform', () => {
  beforeEach(() => {
    vi.resetModules()
  })
  afterEach(() => {
    restorePlatform()
    vi.doUnmock('../../../src/core/shell')
  })

  it('prefers apt on Debian-like Linux', async () => {
    setPlatform('linux')
    vi.doMock('../../../src/core/shell', () => ({
      safeExec: (cmd: string) => (cmd.includes('apt-get') ? '/usr/bin/apt-get' : '')
    }))
    const { installCommandForPlatform } = await import(
      '../../../src/profiles/python/jemallocAllocator'
    )
    const cmd = installCommandForPlatform()
    expect(cmd?.label).toBe('apt')
    expect(cmd?.command).toBe('sudo apt install -y libjemalloc2')
  })

  it('falls through to dnf when apt is absent', async () => {
    setPlatform('linux')
    vi.doMock('../../../src/core/shell', () => ({
      safeExec: (cmd: string) => (cmd.includes('dnf') ? '/usr/bin/dnf' : '')
    }))
    const { installCommandForPlatform } = await import(
      '../../../src/profiles/python/jemallocAllocator'
    )
    expect(installCommandForPlatform()?.label).toBe('dnf')
  })

  it('returns brew command on macOS', async () => {
    setPlatform('darwin')
    const { installCommandForPlatform } = await import(
      '../../../src/profiles/python/jemallocAllocator'
    )
    expect(installCommandForPlatform()?.command).toBe('brew install jemalloc')
  })

  it('returns null on Linux with no supported package manager', async () => {
    setPlatform('linux')
    vi.doMock('../../../src/core/shell', () => ({ safeExec: () => '' }))
    const { installCommandForPlatform } = await import(
      '../../../src/profiles/python/jemallocAllocator'
    )
    expect(installCommandForPlatform()).toBeNull()
  })
})
