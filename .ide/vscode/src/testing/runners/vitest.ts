/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'

import type { DiscoveredTest, JUnitTestCase, RuleScope, RunOptions } from '../types'

export const VITEST_TEST_RULE_REGEX =
  /\bvitest_(?:bin\.)?vitest_test\s*\(\s*[\s\S]*?name\s*=\s*"([^"]+)"/g

export const VITEST_FILE_EXTS = ['.test.ts', '.test.tsx', '.test.vue', '.spec.ts', '.test.js']
export const VITEST_FILE_REGEX = /\.(?:test|spec)\.(?:ts|tsx|mts|cts|js|jsx|mjs|cjs|vue)$/
const VITEST_TEST_NAME_REGEX = /(?:^|\s)(?:test|it)(?:\.[a-z]+)*\s*\(\s*['"`](.+?)['"`]/

export function discoverVitestTestsForTarget(wsPath: string, target: string): DiscoveredTest[] {
  const without = target.replace(/^\/\//, '')
  const colon = without.indexOf(':')
  if (colon < 0) return []
  const pkg = without.slice(0, colon)
  const testsRoot = path.join(wsPath, pkg, 'tests')
  if (!fs.existsSync(testsRoot)) return []

  const tests: DiscoveredTest[] = []
  const walk = (dir: string): void => {
    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue
        walk(full)
      } else if (entry.isFile() && VITEST_FILE_REGEX.test(entry.name)) {
        let content: string
        try {
          content = fs.readFileSync(full, 'utf-8')
        } catch {
          continue
        }
        const lines = content.split('\n')
        const classname = `//${pkg}:${path
          .relative(path.join(wsPath, pkg), full)
          .replace(VITEST_FILE_REGEX, '')
          .replace(/\//g, '.')}`
        for (let i = 0; i < lines.length; i++) {
          const m = VITEST_TEST_NAME_REGEX.exec(lines[i])
          if (m) tests.push({ file: full, line: i, name: m[1], classname })
        }
      }
    }
  }
  walk(testsRoot)
  return tests
}

export function findVitestTestLine(filePath: string, name: string): number | undefined {
  try {
    const content = fs.readFileSync(filePath, 'utf-8')
    const lines = content.split('\n')
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`(?:^|\\s|\\.)(?:test|it)(?:\\.[a-z]+)*\\s*\\(\\s*['"\`]${escaped}['"\`]`)
    for (let i = 0; i < lines.length; i++) {
      if (re.test(lines[i])) return i
    }
  } catch {
    /* ignore */
  }
  return undefined
}

export function vitestCaseToFilePath(
  wsPath: string,
  c: JUnitTestCase,
  targetPkg?: string
): string | undefined {
  if (c.file) {
    const abs = path.isAbsolute(c.file) ? c.file : path.join(wsPath, c.file)
    if (fs.existsSync(abs)) return abs
  }
  // classname format: "//<pkg>:<dotted>" (legacy source-discovery format).
  const m = /^\/\/([^:]+):(.+)$/.exec(c.classname)
  if (m) {
    const inner = m[2].replace(/\./g, '/')
    for (const ext of VITEST_FILE_EXTS) {
      const candidate = path.join(wsPath, m[1], inner + ext)
      if (fs.existsSync(candidate)) return candidate
    }
  }
  // Vitest's default JUnit classname is the source file path relative to the
  // vitest cwd (which under Bazel is the package directory).
  if (targetPkg && c.classname) {
    const direct = path.join(wsPath, targetPkg, c.classname)
    if (fs.existsSync(direct)) return direct
  }
  const parts = c.classname.split('.')
  for (let len = parts.length; len > 0; len--) {
    for (const ext of VITEST_FILE_EXTS) {
      const candidate = path.join(wsPath, ...parts.slice(0, len)) + ext
      if (fs.existsSync(candidate)) return candidate
    }
  }
  return undefined
}

export function vitestCaseFilePath(wsPath: string, c: JUnitTestCase, targetPkg?: string): string {
  const resolved = vitestCaseToFilePath(wsPath, c, targetPkg)
  if (resolved) return resolved
  if (c.file) {
    return path.isAbsolute(c.file) ? c.file : path.join(wsPath, c.file)
  }
  if (targetPkg) return path.join(wsPath, targetPkg, c.classname)
  return path.join(wsPath, c.classname.replace(/\./g, '/') + '.test.ts')
}

/** Vitest JUnit emits test names as "describe > nested > it". Discovery
 *  captures only the `it()` first arg, so the full describe path doesn't
 *  match the existing function item. Strip everything up to and including
 *  the last " > " so reported cases land on the discovered items. */
export function vitestCaseLeafName(name: string): string {
  const idx = name.lastIndexOf(' > ')
  return idx >= 0 ? name.slice(idx + 3) : name
}

export function buildVitestArgs(opts: RunOptions, scope: RuleScope): string[] {
  const args: string[] = []
  for (const f of scope.scopedFilesRel ?? []) {
    args.push(`--test_arg=${f}`)
  }
  const names = scope.scopedTestNames ?? []
  if (names.length > 0) {
    const pattern = names.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
    args.push('--test_arg=-t', `--test_arg=${pattern}`)
  } else if (opts.kFilter) {
    args.push('--test_arg=-t', `--test_arg=${opts.kFilter}`)
  }
  return args
}
