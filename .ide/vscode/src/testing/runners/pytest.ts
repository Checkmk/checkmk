/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'

import type { DiscoveredTest, JUnitTestCase, RunOptions } from '../types'

export const PY_TEST_RULE_REGEX = /\bpy_test\s*\(\s*[\s\S]*?name\s*=\s*"([^"]+)"/g

export function discoverPyTestsForTarget(wsPath: string, target: string): DiscoveredTest[] {
  const without = target.replace(/^\/\//, '')
  const colon = without.indexOf(':')
  if (colon < 0) return []
  const pkg = without.slice(0, colon)
  const root = path.join(wsPath, pkg)
  if (!fs.existsSync(root)) return []

  const tests: DiscoveredTest[] = []
  const fnRegex = /^\s*(?:async\s+)?def\s+(test_\w+)/
  const walk = (dir: string, isRoot: boolean): void => {
    if (!isRoot && fs.existsSync(path.join(dir, 'BUILD'))) return
    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        if (entry.name === '__pycache__' || entry.name.startsWith('.')) continue
        walk(full, false)
      } else if (entry.isFile() && /^test_.*\.py$/.test(entry.name)) {
        let content: string
        try {
          content = fs.readFileSync(full, 'utf-8')
        } catch {
          continue
        }
        const lines = content.split('\n')
        const rel = path.relative(wsPath, full)
        const classname = rel.replace(/\//g, '.').replace(/\.py$/, '')
        for (let i = 0; i < lines.length; i++) {
          const m = fnRegex.exec(lines[i])
          if (m) tests.push({ file: full, line: i, name: m[1], classname })
        }
      }
    }
  }
  walk(root, true)
  return tests
}

export function classnameToPyFilePath(
  base: string,
  classname: string,
  fileHint?: string
): string | undefined {
  if (fileHint) {
    const abs = path.isAbsolute(fileHint) ? fileHint : path.join(base, fileHint)
    if (fs.existsSync(abs)) return abs
  }
  const parts = classname.split('.')
  for (let len = parts.length; len > 0; len--) {
    const candidate = path.join(base, ...parts.slice(0, len)) + '.py'
    if (fs.existsSync(candidate)) return candidate
  }
  return undefined
}

export function findPyTestLine(filePath: string, name: string): number | undefined {
  try {
    const content = fs.readFileSync(filePath, 'utf-8')
    const lines = content.split('\n')
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`^\\s*(?:async\\s+)?def\\s+${escaped}\\b`)
    for (let i = 0; i < lines.length; i++) {
      if (re.test(lines[i])) return i
    }
  } catch {
    /* ignore */
  }
  return undefined
}

export function pyCaseFilePath(wsPath: string, c: JUnitTestCase, targetPkg?: string): string {
  let resolved = classnameToPyFilePath(wsPath, c.classname, c.file)
  if (resolved) return resolved
  if (targetPkg) {
    resolved = classnameToPyFilePath(path.join(wsPath, targetPkg), c.classname, c.file)
    if (resolved) return resolved
  }
  return path.join(wsPath, c.file || c.classname.replace(/\./g, '/') + '.py')
}

export function buildPyTestArgs(opts: RunOptions): string[] {
  if (opts.kFilter) return ['--test_arg=-k', `--test_arg=${opts.kFilter}`]
  return []
}
