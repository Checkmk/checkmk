/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import type { DiscoveredTest } from '../types'

export const PY_DOC_TEST_RULE_REGEX = /\bpy_doc_test\s*\(\s*[\s\S]*?name\s*=\s*"([^"]+)"/g

export function discoverPyDocTestsForTarget(wsPath: string, target: string): DiscoveredTest[] {
  const without = target.replace(/^\/\//, '')
  const colon = without.indexOf(':')
  if (colon < 0) return []
  const pkg = without.slice(0, colon)
  const root = path.join(wsPath, pkg)
  if (!fs.existsSync(root)) return []

  const tests: DiscoveredTest[] = []
  const fnRe = /^\s*(?:async\s+)?def\s+(\w+)/
  const walk = (dir: string): void => {
    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      const full = path.join(dir, e.name)
      if (e.isDirectory()) {
        if (e.name === '__pycache__' || e.name.startsWith('.')) continue
        if (e.name === 'tests' || e.name === 'test') continue
        walk(full)
      } else if (e.isFile() && /\.py$/.test(e.name)) {
        if (/^test_/.test(e.name) || e.name === 'conftest.py') continue
        let content: string
        try {
          content = fs.readFileSync(full, 'utf-8')
        } catch {
          continue
        }
        if (!content.includes('>>>')) continue
        const lines = content.split('\n')
        const rel = path.relative(wsPath, full)
        const classname = rel.replace(/\//g, '.').replace(/\.py$/, '')
        for (let i = 0; i < lines.length; i++) {
          const m = fnRe.exec(lines[i])
          if (!m) continue
          for (let j = i + 1; j < Math.min(lines.length, i + 60); j++) {
            if (fnRe.test(lines[j])) break
            if (lines[j].includes('>>>')) {
              tests.push({ file: full, line: i, name: m[1], classname })
              break
            }
          }
        }
      }
    }
  }
  walk(root)
  return tests
}

export interface PyDocReportContext {
  run: vscode.TestRun
  item: vscode.TestItem
  durationMs: number
  exitCode: number
  cancelled: boolean
  scopedItems?: vscode.TestItem[]
}

export function reportPyDocTestRun(ctx: PyDocReportContext): void {
  const { run, item, durationMs, exitCode, cancelled, scopedItems } = ctx
  const visit = (
    node: vscode.TestItem,
    mark: 'passed' | 'failed' | 'skipped',
    msg?: vscode.TestMessage
  ): void => {
    if (mark === 'passed') run.passed(node, durationMs)
    else if (mark === 'skipped') run.skipped(node)
    else run.failed(node, [msg ?? new vscode.TestMessage('doctest failed')], durationMs)
    node.children.forEach((c) => visit(c, mark, msg))
  }
  const propagate = (mark: 'passed' | 'failed' | 'skipped', msg?: vscode.TestMessage): void => {
    visit(item, mark, msg)
    if (scopedItems) for (const ci of scopedItems) visit(ci, mark, msg)
  }
  if (cancelled) {
    propagate('skipped')
  } else if (exitCode === 0) {
    propagate('passed')
  } else {
    propagate('failed', new vscode.TestMessage(`bazel test exited ${exitCode}`))
  }
}
