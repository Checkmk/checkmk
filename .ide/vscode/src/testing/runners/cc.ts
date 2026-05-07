/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { stripAnsi } from '../junit'
import { spawnAndCollect, targetBinaryPath } from '../process'
import type { JUnitTestCase, RuleScope } from '../types'

export const CC_TEST_RULE_REGEX = /\bcc_test\s*\(\s*[\s\S]*?name\s*=\s*"([^"]+)"/g

const CC_LOC_CACHE = new Map<string, Map<string, { uri: vscode.Uri; line: number }>>()

function buildCcLocationMap(
  wsPath: string,
  targetPkg: string
): Map<string, { uri: vscode.Uri; line: number }> {
  const cached = CC_LOC_CACHE.get(targetPkg)
  if (cached) return cached
  const map = new Map<string, { uri: vscode.Uri; line: number }>()
  const macroRe = /\bTEST(?:_F|_P)?\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)/
  const walk = (dir: string): void => {
    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      const full = path.join(dir, e.name)
      if (e.isDirectory()) walk(full)
      else if (e.isFile() && /\.(cc|cpp|cxx|c)$/.test(e.name)) {
        let content: string
        try {
          content = fs.readFileSync(full, 'utf-8')
        } catch {
          continue
        }
        const lines = content.split('\n')
        for (let i = 0; i < lines.length; i++) {
          const m = macroRe.exec(lines[i])
          if (m) {
            const key = `${m[1]}.${m[2]}`
            if (!map.has(key)) map.set(key, { uri: vscode.Uri.file(full), line: i })
          }
        }
      }
    }
  }
  for (const d of ['test', 'tests']) {
    const root = path.join(wsPath, targetPkg, d)
    if (fs.existsSync(root)) walk(root)
  }
  CC_LOC_CACHE.set(targetPkg, map)
  return map
}

export function ccFullNameFromItemId(targetId: string, itemId: string): string | undefined {
  const prefix = `${targetId}::F::__cc__::`
  if (!itemId.startsWith(prefix)) return undefined
  return itemId.slice(prefix.length)
}

export function getOrCreateCcFunctionItem(
  controller: vscode.TestController,
  targetItem: vscode.TestItem,
  fullName: string,
  wsPath: string,
  fileHint?: string,
  lineHint?: number
): vscode.TestItem {
  const dot = fullName.indexOf('.')
  const suite = dot < 0 ? fullName : fullName.slice(0, dot)
  const test = dot < 0 ? '' : fullName.slice(dot + 1)
  const targetPkg = targetItem.id.replace(/^\/\//, '').split(':')[0]

  const suiteId = `${targetItem.id}::D::${suite}`
  let suiteItem = targetItem.children.get(suiteId)
  if (!suiteItem) {
    suiteItem = controller.createTestItem(suiteId, suite, undefined)
    targetItem.children.add(suiteItem)
  }

  const id = `${targetItem.id}::F::__cc__::${fullName}`
  const existing = suiteItem.children.get(id)
  if (existing) return existing

  let uri: vscode.Uri | undefined
  let line: number | undefined
  if (fileHint) {
    const abs = path.isAbsolute(fileHint) ? fileHint : path.join(wsPath, fileHint)
    if (fs.existsSync(abs)) {
      uri = vscode.Uri.file(abs)
      line = lineHint !== undefined ? lineHint - 1 : undefined
    }
  }
  if (!uri) {
    const loc = buildCcLocationMap(wsPath, targetPkg).get(fullName)
    if (loc) {
      uri = loc.uri
      line = loc.line
    }
  }
  const item = controller.createTestItem(id, test, uri)
  if (line !== undefined && line >= 0) item.range = new vscode.Range(line, 0, line, 0)
  suiteItem.children.add(item)
  return item
}

function parseGtestList(buf: string): string[] {
  const text = stripAnsi(buf)
  const names: string[] = []
  let suite = ''
  for (const line of text.split('\n')) {
    const sm = /^(\S+)\.\s*$/.exec(line)
    if (sm) {
      suite = sm[1]
      continue
    }
    const tm = /^\s+(\S+)/.exec(line)
    if (tm && suite) {
      names.push(`${suite}.${tm[1]}`)
    } else if (line.trim() === '') {
      /* keep suite */
    } else {
      suite = ''
    }
  }
  return names
}

export async function listCcTestNames(wsPath: string, target: string): Promise<string[]> {
  const bin = targetBinaryPath(wsPath, target)
  if (fs.existsSync(bin)) {
    const out = await spawnAndCollect(bin, ['--gtest_list_tests'], wsPath)
    const names = parseGtestList(out)
    if (names.length > 0) return names
  }
  const without = target.replace(/^\/\//, '')
  const colon = without.indexOf(':')
  if (colon >= 0) {
    const pkg = without.slice(0, colon)
    const sourceNames = Array.from(buildCcLocationMap(wsPath, pkg).keys())
    if (sourceNames.length > 0) return sourceNames
  }
  const out = await spawnAndCollect(
    'bazel',
    [
      'test',
      target,
      '--test_output=streamed',
      '--test_arg=--gtest_list_tests',
      '--cache_test_results=no'
    ],
    wsPath
  )
  return parseGtestList(out)
}

export async function ensureCcDiscovered(
  controller: vscode.TestController,
  item: vscode.TestItem,
  wsPath: string
): Promise<void> {
  if (item.children.size > 0) return
  const names = await listCcTestNames(wsPath, item.id)
  for (const name of names) {
    getOrCreateCcFunctionItem(controller, item, name, wsPath)
  }
}

export function buildCcArgs(scope: RuleScope): string[] {
  const names = scope.scopedTestNames ?? []
  if (names.length > 0) {
    return [`--test_arg=--gtest_filter=${names.join(':')}`]
  }
  return []
}

export interface CcReportContext {
  controller: vscode.TestController
  run: vscode.TestRun
  item: vscode.TestItem
  wsPath: string
  durationMs: number
  exitCode: number
  cancelled: boolean
  cases: JUnitTestCase[]
  reportCase: (item: vscode.TestItem, c: JUnitTestCase) => void
}

export function reportCcTestRun(ctx: CcReportContext): void {
  const { controller, run, item, wsPath, durationMs, exitCode, cancelled, cases, reportCase } = ctx
  for (const c of cases) {
    const fullName = c.classname ? `${c.classname}.${c.name}` : c.name
    const funcItem = getOrCreateCcFunctionItem(controller, item, fullName, wsPath, c.file, c.line)
    reportCase(funcItem, c)
  }
  if (cancelled) {
    run.skipped(item)
  } else if (cases.length === 0) {
    if (exitCode === 0) run.passed(item, durationMs)
    else run.failed(item, [new vscode.TestMessage(`bazel test exited ${exitCode}`)], durationMs)
  } else {
    const failed = cases.filter((c) => c.status === 'failed' || c.status === 'error').length
    if (failed > 0) {
      run.failed(item, [new vscode.TestMessage(`${failed} test(s) failed`)], durationMs)
    } else if (cases.every((c) => c.status === 'skipped')) {
      run.skipped(item)
    } else {
      run.passed(item, durationMs)
    }
  }
}
