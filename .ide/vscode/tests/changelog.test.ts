/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { existsSync, readFileSync } from 'fs'
import path from 'path'
import { describe, expect, it } from 'vitest'

const EXTENSION_ROOT = path.resolve(__dirname, '..')
const PACKAGE_JSON = path.join(EXTENSION_ROOT, 'package.json')
const CHANGELOG_DIR = path.join(EXTENSION_ROOT, 'changelog')

function currentVersion(): string {
  const pkg = JSON.parse(readFileSync(PACKAGE_JSON, 'utf8'))
  return pkg.version as string
}

describe('changelog', () => {
  it('has a changelog entry for the current package.json version', () => {
    const version = currentVersion()
    const file = path.join(CHANGELOG_DIR, `v${version}.md`)
    expect(
      existsSync(file),
      `Missing ${path.relative(EXTENSION_ROOT, file)}. Run \`bazel run //.ide/vscode:generate_changelog\` after bumping the version.`
    ).toBe(true)
  })

  it('changelog entry is non-empty and starts with the version header', () => {
    const version = currentVersion()
    const file = path.join(CHANGELOG_DIR, `v${version}.md`)
    if (!existsSync(file)) return // covered by the previous test
    const content = readFileSync(file, 'utf8')
    expect(content.length).toBeGreaterThan(0)
    expect(content.split('\n')[0]).toBe(`## v${version}`)
  })
})
