/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { PipxUpdateCheck } from '../../src/core/pipxUpdate'

describe('PipxUpdateCheck', () => {
  it('reads the version of exactly the named package from pipx list --short', () => {
    const listing = 'cmk-dev-site 1.23.0\ncmk-werk-zeug 0.4.10\ncmk-werk-zeug-extra 9.9.9\n'
    expect(PipxUpdateCheck.parseVersion(listing, 'cmk-werk-zeug')).toBe('0.4.10')
  })

  it('reports no version when the package is not installed', () => {
    expect(PipxUpdateCheck.parseVersion('cmk-dev-site 1.23.0\n', 'cmk-werk-zeug')).toBe('')
  })

  it('reads the newest release from the PyPI JSON and tolerates garbage', () => {
    expect(PipxUpdateCheck.parsePypiVersion('{"info": {"version": "0.4.12"}}')).toBe('0.4.12')
    expect(PipxUpdateCheck.parsePypiVersion('<html>')).toBe('')
  })

  it('upgrades a global install with sudo and a user install without', () => {
    expect(PipxUpdateCheck.upgradeCommand('cmk-werk-zeug', true)).toBe(
      'sudo pipx upgrade --global cmk-werk-zeug'
    )
    expect(PipxUpdateCheck.upgradeCommand('cmk-werk-zeug', false)).toBe(
      'pipx upgrade cmk-werk-zeug'
    )
  })
})
