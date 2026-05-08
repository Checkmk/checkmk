/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { extractSystemOut, stripAnsi } from '../junit'
import { spawnAndCollect, targetBinaryPath } from '../process'
import type { JUnitTestCase, RuleScope } from '../types'

export const RUST_TEST_RULE_REGEX = /\brust_test\s*\(\s*[\s\S]*?name\s*=\s*"([^"]+)"/g

export function parseLibtestOutput(rawText: string): JUnitTestCase[] {
  const text = stripAnsi(rawText)
  const failures = new Map<string, string>()
  const blockRe = /---- (\S+) stdout ----\n([\s\S]*?)(?=\n----|\nfailures:|\ntest result:|$)/g
  let fm: RegExpExecArray | null
  while ((fm = blockRe.exec(text)) !== null) {
    failures.set(fm[1], fm[2].trim())
  }
  const cases: JUnitTestCase[] = []
  const lineRe = /^test (\S+) \.\.\. (ok|FAILED|ignored)\b/gm
  let m: RegExpExecArray | null
  while ((m = lineRe.exec(text)) !== null) {
    const [, name, status] = m
    cases.push({
      classname: '',
      name,
      time: 0,
      status: status === 'ok' ? 'passed' : status === 'ignored' ? 'skipped' : 'failed',
      details: status === 'FAILED' ? failures.get(name) : undefined
    })
  }
  return cases
}

function parseLibtestList(buf: string): string[] {
  const text = stripAnsi(buf)
  const names: string[] = []
  const re = /^(\S+):\s*test(?:\s|$)/
  for (const line of text.split('\n')) {
    const m = re.exec(line)
    if (m) names.push(m[1])
  }
  return names
}

const RUST_TEST_ATTR_RE =
  /^\s*#\[(?:test|tokio::test|async_std::test|rstest|wasm_bindgen_test|test_case|googletest::test)/
const RUST_TEST_ATTR_FILE_RE =
  /^\s*#\[(?:test|tokio::test|async_std::test|rstest|wasm_bindgen_test|test_case|googletest::test)/m
const RUST_MOD_OPEN_RE = /^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+(\w+)\s*\{/
const RUST_FN_RE = /^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)/

function deriveRustModulePath(filePath: string, root: string): string[] {
  const rel = path.relative(root, filePath).replace(/\.rs$/, '')
  const segs = rel.split(path.sep)
  const last = segs[segs.length - 1]
  if (last === 'mod' || last === 'lib' || last === 'main') segs.pop()
  return segs
}

export function parseRustTestsFromFile(
  content: string,
  baseModulePath: string[]
): { fullName: string; line: number }[] {
  const out: { fullName: string; line: number }[] = []
  const modStack = [...baseModulePath]
  const modPopAt: number[] = []
  let depth = 0
  let testPending = false
  const lines = content.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (RUST_TEST_ATTR_RE.test(line)) testPending = true
    const modMatch = RUST_MOD_OPEN_RE.exec(line)
    if (modMatch) {
      modStack.push(modMatch[1])
      modPopAt.push(depth + 1)
    }
    const fnMatch = RUST_FN_RE.exec(line)
    if (fnMatch) {
      if (testPending) {
        out.push({ fullName: [...modStack, fnMatch[1]].join('::'), line: i })
      }
      testPending = false
    }
    for (const ch of line) {
      if (ch === '{') depth++
      else if (ch === '}') {
        depth--
        while (modPopAt.length > 0 && modPopAt[modPopAt.length - 1] > depth) {
          modPopAt.pop()
          modStack.pop()
        }
      }
    }
  }
  return out
}

function discoverRustTestNamesFromSource(wsPath: string, target: string): string[] {
  const without = target.replace(/^\/\//, '')
  const colon = without.indexOf(':')
  if (colon < 0) return []
  const pkg = without.slice(0, colon)
  const seen = new Set<string>()
  const walk = (root: string): void => {
    const visit = (dir: string): void => {
      let entries: fs.Dirent[]
      try {
        entries = fs.readdirSync(dir, { withFileTypes: true })
      } catch {
        return
      }
      for (const e of entries) {
        const full = path.join(dir, e.name)
        if (e.isDirectory()) {
          if (e.name.startsWith('.') || e.name === 'target') continue
          visit(full)
        } else if (e.isFile() && e.name.endsWith('.rs')) {
          let content: string
          try {
            content = fs.readFileSync(full, 'utf-8')
          } catch {
            continue
          }
          if (!RUST_TEST_ATTR_FILE_RE.test(content)) continue
          const base = deriveRustModulePath(full, root)
          for (const t of parseRustTestsFromFile(content, base)) seen.add(t.fullName)
        }
      }
    }
    visit(root)
  }
  for (const d of ['src', 'tests']) {
    const root = path.join(wsPath, pkg, d)
    if (fs.existsSync(root)) walk(root)
  }
  return Array.from(seen)
}

export async function listRustTestNames(wsPath: string, target: string): Promise<string[]> {
  const bin = targetBinaryPath(wsPath, target)
  if (fs.existsSync(bin)) {
    const out = await spawnAndCollect(bin, ['--list'], wsPath)
    const names = parseLibtestList(out)
    if (names.length > 0) return names
  }
  const sourceNames = discoverRustTestNamesFromSource(wsPath, target)
  if (sourceNames.length > 0) return sourceNames
  const out = await spawnAndCollect(
    'bazel',
    ['test', target, '--test_output=streamed', '--test_arg=--list', '--cache_test_results=no'],
    wsPath
  )
  return parseLibtestList(out)
}

function resolveRustModuleUri(
  wsPath: string,
  targetPkg: string,
  modulePath: string[]
): vscode.Uri | undefined {
  if (modulePath.length === 0) return undefined
  const last = modulePath[modulePath.length - 1]
  const head = modulePath.slice(0, -1)
  const candidates = [
    path.join(wsPath, targetPkg, 'src', ...head, last + '.rs'),
    path.join(wsPath, targetPkg, 'src', ...modulePath, 'mod.rs'),
    path.join(wsPath, targetPkg, 'tests', ...head, last + '.rs'),
    path.join(wsPath, targetPkg, 'tests', ...modulePath, 'mod.rs'),
    path.join(wsPath, targetPkg, 'src', ...head) + '.rs',
    path.join(wsPath, targetPkg, 'tests', ...head) + '.rs'
  ]
  for (const c of candidates) {
    if (fs.existsSync(c)) return vscode.Uri.file(c)
  }
  return undefined
}

function findRustTestLine(filePath: string, funcName: string): number | undefined {
  try {
    const content = fs.readFileSync(filePath, 'utf-8')
    const lines = content.split('\n')
    const escaped = funcName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`^\\s*(?:pub\\s+)?(?:async\\s+)?fn\\s+${escaped}\\b`)
    for (let i = 0; i < lines.length; i++) {
      if (re.test(lines[i])) return i
    }
  } catch {
    /* ignore */
  }
  return undefined
}

function findRustFnInPackage(
  wsPath: string,
  targetPkg: string,
  funcName: string
): { uri: vscode.Uri; line: number } | undefined {
  const escaped = funcName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`^\\s*(?:pub(?:\\([^)]*\\))?\\s+)?(?:async\\s+)?fn\\s+${escaped}\\b`)
  const visit = (dir: string): { uri: vscode.Uri; line: number } | undefined => {
    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return undefined
    }
    for (const e of entries) {
      const full = path.join(dir, e.name)
      if (e.isDirectory()) {
        if (e.name.startsWith('.') || e.name === 'target') continue
        const r = visit(full)
        if (r) return r
      } else if (e.isFile() && e.name.endsWith('.rs')) {
        let content: string
        try {
          content = fs.readFileSync(full, 'utf-8')
        } catch {
          continue
        }
        const lines = content.split('\n')
        for (let i = 0; i < lines.length; i++) {
          if (re.test(lines[i])) return { uri: vscode.Uri.file(full), line: i }
        }
      }
    }
    return undefined
  }
  for (const d of ['tests', 'src']) {
    const root = path.join(wsPath, targetPkg, d)
    if (!fs.existsSync(root)) continue
    const r = visit(root)
    if (r) return r
  }
  return undefined
}

function getOrCreateRustModuleChain(
  controller: vscode.TestController,
  targetItem: vscode.TestItem,
  modulePath: string[],
  wsPath: string
): vscode.TestItem {
  if (modulePath.length === 0) return targetItem
  const targetPkg = targetItem.id.replace(/^\/\//, '').split(':')[0]
  let cur = targetItem
  const cum: string[] = []
  for (const seg of modulePath) {
    cum.push(seg)
    const id = `${targetItem.id}::D::${cum.join('.')}`
    let child = cur.children.get(id)
    if (!child) {
      const uri = resolveRustModuleUri(wsPath, targetPkg, [...cum])
      child = controller.createTestItem(id, seg, uri)
      cur.children.add(child)
    }
    cur = child
  }
  return cur
}

export function rustFullNameFromItemId(targetId: string, itemId: string): string | undefined {
  const prefix = `${targetId}::F::__rust__::`
  if (!itemId.startsWith(prefix)) return undefined
  return itemId.slice(prefix.length)
}

export function getOrCreateRustFunctionItem(
  controller: vscode.TestController,
  targetItem: vscode.TestItem,
  fullName: string,
  wsPath: string
): vscode.TestItem {
  const segments = fullName.split('::')
  const funcName = segments[segments.length - 1]
  const modulePath = segments.slice(0, -1)
  const parent = getOrCreateRustModuleChain(controller, targetItem, modulePath, wsPath)
  const id = `${targetItem.id}::F::__rust__::${fullName}`
  const existing = parent.children.get(id)
  if (existing) return existing
  const targetPkg = targetItem.id.replace(/^\/\//, '').split(':')[0]
  let fileUri = resolveRustModuleUri(wsPath, targetPkg, modulePath)
  let line: number | undefined
  if (fileUri) {
    line = findRustTestLine(fileUri.fsPath, funcName)
  }
  if (!fileUri || line === undefined) {
    const found = findRustFnInPackage(wsPath, targetPkg, funcName)
    if (found) {
      fileUri = found.uri
      line = found.line
    }
  }
  const item = controller.createTestItem(id, funcName, fileUri)
  if (line !== undefined) item.range = new vscode.Range(line, 0, line, 0)
  parent.children.add(item)
  return item
}

export async function ensureRustDiscovered(
  controller: vscode.TestController,
  item: vscode.TestItem,
  wsPath: string
): Promise<void> {
  if (item.children.size > 0) return
  const names = await listRustTestNames(wsPath, item.id)
  for (const name of names) {
    getOrCreateRustFunctionItem(controller, item, name, wsPath)
  }
}

export function buildRustArgs(scope: RuleScope): string[] {
  const args: string[] = []
  const names = scope.scopedTestNames ?? []
  if (names.length > 0) {
    for (const n of names) args.push(`--test_arg=${n}`)
    args.push('--test_arg=--exact')
  }
  return args
}

export interface RustReportContext {
  controller: vscode.TestController
  run: vscode.TestRun
  item: vscode.TestItem
  wsPath: string
  durationMs: number
  exitCode: number
  cancelled: boolean
  xmlContent: string
  reportCase: (item: vscode.TestItem, c: JUnitTestCase) => void
  scopedItems?: vscode.TestItem[]
}

export function reportRustTestRun(ctx: RustReportContext): void {
  const {
    controller,
    run,
    item,
    wsPath,
    durationMs,
    exitCode,
    cancelled,
    xmlContent,
    reportCase,
    scopedItems
  } = ctx
  const sysOut = extractSystemOut(xmlContent)
  const rustCases = parseLibtestOutput(sysOut)
  for (const c of rustCases) {
    const funcItem = getOrCreateRustFunctionItem(controller, item, c.name, wsPath)
    reportCase(funcItem, c)
  }
  if (cancelled) {
    run.skipped(item)
    if (scopedItems) for (const ci of scopedItems) run.skipped(ci)
  } else if (rustCases.length === 0) {
    if (exitCode === 0) {
      run.passed(item, durationMs)
      if (scopedItems) for (const ci of scopedItems) run.passed(ci, durationMs)
    } else {
      const msg = new vscode.TestMessage(`bazel test exited ${exitCode}`)
      run.failed(item, [msg], durationMs)
      if (scopedItems) for (const ci of scopedItems) run.failed(ci, [msg], durationMs)
    }
  } else {
    const failed = rustCases.filter((c) => c.status === 'failed' || c.status === 'error').length
    if (failed > 0) {
      run.failed(item, [new vscode.TestMessage(`${failed} test(s) failed`)], durationMs)
    } else if (rustCases.every((c) => c.status === 'skipped')) {
      run.skipped(item)
    } else {
      run.passed(item, durationMs)
    }
  }
}
