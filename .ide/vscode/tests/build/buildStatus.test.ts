/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { checkBuildStatus, sharedTypingConsumers } from '../../src/build/buildStatus'

let wsPath: string

function writeBuild(pkg: string, content: string): void {
  fs.mkdirSync(path.join(wsPath, pkg), { recursive: true })
  fs.writeFileSync(path.join(wsPath, pkg, 'BUILD'), content)
}

beforeEach(() => {
  wsPath = fs.mkdtempSync(path.join(os.tmpdir(), 'cmk-build-status-'))
})

afterEach(() => {
  fs.rmSync(wsPath, { recursive: true, force: true })
})

describe('sharedTypingConsumers', () => {
  it('finds the packages that link shared typing, free and non-free', () => {
    writeBuild(
      'packages/cmk-profiling',
      'link_shared_typing()\n\nvitest_test(name = "unit-test")\n'
    )
    writeBuild('non-free/packages/cmk-ai', 'link_shared_typing()\n')
    writeBuild('packages/cmk-ccc', 'py_library(name = "ccc")\n')
    writeBuild(
      'packages/cmk-load-only',
      'load("//bazel/rules:link_shared_typing.bzl", "link_shared_typing")\n'
    )

    expect(sharedTypingConsumers(wsPath).sort()).toEqual([
      path.join('non-free', 'packages', 'cmk-ai'),
      path.join('packages', 'cmk-profiling')
    ])
  })

  it('finds no packages in a checkout without package roots', () => {
    expect(sharedTypingConsumers(wsPath)).toEqual([])
  })
})

describe('checkBuildStatus', () => {
  it('needs no shared-typing link in a checkout without consumers', () => {
    expect(checkBuildStatus(wsPath).sharedTypingTs.ok).toBe(true)
  })

  it('needs the shared-typing link in every consumer', () => {
    writeBuild('packages/cmk-profiling', 'link_shared_typing()\n')

    expect(checkBuildStatus(wsPath).sharedTypingTs.ok).toBe(false)
  })
})
