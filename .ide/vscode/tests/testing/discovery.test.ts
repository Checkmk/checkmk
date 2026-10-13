/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { discoverTargetsFromFilesystem } from '../../src/testing/discovery'

let wsPath: string

function writeBuild(pkg: string, content: string): void {
  const dir = path.join(wsPath, pkg)
  fs.mkdirSync(dir, { recursive: true })
  fs.writeFileSync(path.join(dir, 'BUILD'), content)
}

beforeEach(() => {
  wsPath = fs.mkdtempSync(path.join(os.tmpdir(), 'cmk-discovery-'))
})

afterEach(() => {
  fs.rmSync(wsPath, { recursive: true, force: true })
})

describe('discoverTargetsFromFilesystem', () => {
  it('discovers py_cmk_test targets, the macro the repo actually uses', async () => {
    writeBuild(
      'tests/unit',
      `load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "repo_community",
    size = "small",
    srcs = ["__init__.py"],
)
`
    )

    const targets = await discoverTargetsFromFilesystem(wsPath)

    expect(targets).toEqual([{ label: '//tests/unit:repo_community', kind: 'py_test' }])
  })

  it('discovers plain py_test targets alongside py_cmk_test ones', async () => {
    writeBuild(
      'tests/unit',
      `py_cmk_test(
    name = "smoke",
)

py_test(
    name = "plain",
)
`
    )

    const targets = await discoverTargetsFromFilesystem(wsPath)

    expect(targets.map((t) => t.label).sort()).toEqual(['//tests/unit:plain', '//tests/unit:smoke'])
  })

  it('does not mistake a py_cmk_test.bzl load statement for a target', async () => {
    writeBuild(
      'tests/unit',
      `load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "conftest",
)
`
    )

    const targets = await discoverTargetsFromFilesystem(wsPath)

    expect(targets).toEqual([])
  })

  it('discovers vitest_test targets from both the macro and the npm binary rule', async () => {
    writeBuild(
      'packages/app',
      `load("//bazel/rules:vitest_test.bzl", "vitest_test")

vitest_test(
    name = "unit-test",
    workers = 3,
)

vitest_bin.vitest_test(
    name = "legacy",
)
`
    )

    const targets = await discoverTargetsFromFilesystem(wsPath)

    expect(targets.sort((a, b) => a.label.localeCompare(b.label))).toEqual([
      { label: '//packages/app:legacy', kind: 'vitest_test' },
      { label: '//packages/app:unit-test', kind: 'vitest_test' }
    ])
  })

  it('discovers the unit-test target that vue_package generates', async () => {
    writeBuild(
      'packages/cmk-ui-library',
      `load("//bazel/rules:vue_package.bzl", "vue_package")

vue_package(
    name = "cmk-ui-library",
    test_deps = [":node_modules/msw"],
)
`
    )

    const targets = await discoverTargetsFromFilesystem(wsPath)

    expect(targets).toEqual([{ label: '//packages/cmk-ui-library:unit-test', kind: 'vitest_test' }])
  })
})
