/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { parseVersion, versionAtLeast } from '../../../src/core/version'
import { buildMypyIniContent, selectDmypyPidsToKill } from '../../../src/profiles/python/mypyConfig'

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

describe('selectDmypyPidsToKill', () => {
  const hash = '389a6ba29756d77fccde5d65d4a378e3daa5d34d'
  const daemonLine = (pid: number, extHostPid: number): string =>
    `${pid} /ws/.venv/bin/python3 /ws/.venv/bin/dmypy --status-file ` +
    `/home/u/.config/Code/User/workspaceStorage/abc/matangover.mypy/dmypy-${hash}-${extHostPid}.json ` +
    `run --log-file /home/u/.config/Code/User/workspaceStorage/abc/matangover.mypy/dmypy-${hash}.log ` +
    `-- --python-executable /ws/.venv/bin/python cmk`

  const myPid = 398482

  it('kills every daemon in killAll mode regardless of owner liveness', () => {
    const lines = [daemonLine(101, myPid), daemonLine(102, 555), daemonLine(103, 777)]
    const result = selectDmypyPidsToKill(lines, {
      killAll: true,
      myExtHostPid: myPid,
      isAlive: () => true
    })
    expect(result).toEqual([101, 102, 103])
  })

  it('spares the current window own daemon in periodic mode', () => {
    const result = selectDmypyPidsToKill([daemonLine(101, myPid)], {
      killAll: false,
      myExtHostPid: myPid,
      isAlive: () => false
    })
    expect(result).toEqual([])
  })

  it('spares a sibling daemon whose owning window is still alive', () => {
    const result = selectDmypyPidsToKill([daemonLine(102, 555)], {
      killAll: false,
      myExtHostPid: myPid,
      isAlive: (pid) => pid === 555
    })
    expect(result).toEqual([])
  })

  it('kills an orphaned daemon whose owning window is gone', () => {
    const result = selectDmypyPidsToKill([daemonLine(103, 777)], {
      killAll: false,
      myExtHostPid: myPid,
      isAlive: () => false
    })
    expect(result).toEqual([103])
  })

  it('reclaims only orphans, keeping own and live-sibling daemons', () => {
    const lines = [daemonLine(101, myPid), daemonLine(102, 555), daemonLine(103, 777)]
    const result = selectDmypyPidsToKill(lines, {
      killAll: false,
      myExtHostPid: myPid,
      isAlive: (pid) => pid === 555
    })
    expect(result).toEqual([103])
  })

  it('spares a daemon whose owner cannot be determined', () => {
    const line = '104 /ws/.venv/bin/dmypy --status-file /tmp/weird.json daemon'
    const result = selectDmypyPidsToKill([line], {
      killAll: false,
      myExtHostPid: myPid,
      isAlive: () => false
    })
    expect(result).toEqual([])
  })

  it('skips transient dmypy client invocations', () => {
    const client = '200 /ws/.venv/bin/dmypy run -- cmk'
    const result = selectDmypyPidsToKill([client, daemonLine(103, 777), ''], {
      killAll: false,
      myExtHostPid: myPid,
      isAlive: () => false
    })
    expect(result).toEqual([103])
  })
})
