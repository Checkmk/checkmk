/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { spawn } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { error, log, notifyError, notifyInfo } from '../../core/log'
import { getExtendedPath } from '../../core/tasks'

const EDITIONS = ['community', 'pro', 'ultimate', 'ultimatemt', 'cloud'] as const

interface RunOptions {
  edition: string
  kFilter?: string
}

export interface JUnitTestCase {
  classname: string
  name: string
  file?: string
  line?: number
  time: number
  status: 'passed' | 'failed' | 'skipped' | 'error'
  message?: string
  details?: string
}

function getWorkspacePath(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

function getRunOptions(): RunOptions {
  const cfg = vscode.workspace.getConfiguration('cmk.bazelTests')
  return {
    edition: cfg.get<string>('edition') || 'pro'
  }
}

function buildBazelArgs(target: string, opts: RunOptions): string[] {
  const args = [
    'test',
    target,
    `--cmk_edition=${opts.edition}`,
    '--test_output=streamed',
    '--test_summary=detailed'
  ]
  if (opts.kFilter) {
    args.push('--test_arg=-k', `--test_arg=${opts.kFilter}`)
  }
  return args
}

function targetToTestXmlPath(wsPath: string, target: string): string {
  const without = target.replace(/^\/\//, '')
  const idx = without.indexOf(':')
  const pkg = idx >= 0 ? without.slice(0, idx) : without
  const name = idx >= 0 ? without.slice(idx + 1) : ''
  return path.join(wsPath, 'bazel-testlogs', pkg, name, 'test.xml')
}

function decodeXml(s: string): string {
  return s
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, '&')
}

export function parseJunitXml(xml: string): JUnitTestCase[] {
  const cases: JUnitTestCase[] = []
  const tcRegex = /<testcase\b([^>]*?)(?:\/>|>([\s\S]*?)<\/testcase>)/g
  const attr = (s: string, k: string): string | undefined => {
    const r = new RegExp(`\\b${k}="([^"]*)"`).exec(s)
    return r ? decodeXml(r[1]) : undefined
  }
  let m: RegExpExecArray | null
  while ((m = tcRegex.exec(xml)) !== null) {
    const attrs = m[1]
    const body = m[2] || ''
    const classname = attr(attrs, 'classname') || ''
    const name = attr(attrs, 'name') || ''
    if (!name) continue
    const time = parseFloat(attr(attrs, 'time') || '0')
    const file = attr(attrs, 'file')
    const lineStr = attr(attrs, 'line')
    const line = lineStr ? parseInt(lineStr, 10) : undefined
    let status: JUnitTestCase['status'] = 'passed'
    let message: string | undefined
    let details: string | undefined
    const failure = /<(failure|error)\b([^>]*?)(?:\/>|>([\s\S]*?)<\/\1>)/.exec(body)
    const skipped = /<skipped\b([^>]*?)(?:\/>|>([\s\S]*?)<\/skipped>)/.exec(body)
    if (failure) {
      status = failure[1] === 'failure' ? 'failed' : 'error'
      message = attr(failure[2], 'message')
      details = decodeXml((failure[3] || '').trim()) || undefined
    } else if (skipped) {
      status = 'skipped'
      message = attr(skipped[1], 'message')
    }
    cases.push({ classname, name, file, line, time, status, message, details })
  }
  return cases
}

function classnameToFilePath(
  wsPath: string,
  classname: string,
  fileHint?: string
): string | undefined {
  if (fileHint) {
    const abs = path.isAbsolute(fileHint) ? fileHint : path.join(wsPath, fileHint)
    if (fs.existsSync(abs)) return abs
  }
  const parts = classname.split('.')
  for (let len = parts.length; len > 0; len--) {
    const candidate = path.join(wsPath, ...parts.slice(0, len)) + '.py'
    if (fs.existsSync(candidate)) return candidate
  }
  return undefined
}

function findTestFunctionLine(filePath: string, name: string): number | undefined {
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

function spawnEnv(): NodeJS.ProcessEnv {
  return { ...process.env, PATH: getExtendedPath() }
}

const SKIP_DIRS = new Set([
  '__pycache__',
  'qa-test-data',
  'typeshed',
  'data',
  'fixtures',
  'node_modules',
  '.venv'
])

const PY_TEST_RULE_REGEX = /\bpy_test\s*\(\s*[\s\S]*?name\s*=\s*"([^"]+)"/g

export async function discoverTargetsFromFilesystem(wsPath: string): Promise<string[]> {
  const labels: string[] = []
  const testsRoot = path.join(wsPath, 'tests')
  if (!fs.existsSync(testsRoot)) return labels
  let processedDirs = 0
  const walk = async (dir: string): Promise<void> => {
    let entries: fs.Dirent[]
    try {
      entries = await fs.promises.readdir(dir, { withFileTypes: true })
    } catch {
      return
    }
    if (entries.some((e) => e.isFile() && e.name === 'BUILD')) {
      try {
        const content = await fs.promises.readFile(path.join(dir, 'BUILD'), 'utf-8')
        PY_TEST_RULE_REGEX.lastIndex = 0
        const pkg = path.relative(wsPath, dir)
        let m: RegExpExecArray | null
        while ((m = PY_TEST_RULE_REGEX.exec(content)) !== null) {
          labels.push(`//${pkg}:${m[1]}`)
        }
      } catch {
        /* ignore */
      }
    }
    if (++processedDirs % 64 === 0) {
      await new Promise<void>((resolve) => setImmediate(resolve))
    }
    for (const entry of entries) {
      if (!entry.isDirectory()) continue
      if (SKIP_DIRS.has(entry.name) || entry.name.startsWith('.')) continue
      if (entry.name.startsWith('bazel-')) continue
      await walk(path.join(dir, entry.name))
    }
  }
  await walk(testsRoot)
  return labels
}

function populateRootPackages(
  controller: vscode.TestController,
  labels: string[],
  wsPath: string
): void {
  const topPkgs = new Set<string>()
  for (const label of labels) {
    const pkg = label.replace(/^\/\//, '').split(':')[0]
    if (!pkg.startsWith('tests')) continue
    const second = pkg.split('/')[1]
    topPkgs.add(second ? `tests/${second}` : 'tests')
  }
  const items: vscode.TestItem[] = []
  for (const pkg of Array.from(topPkgs).sort()) {
    const item = controller.createTestItem(
      `//${pkg}`,
      path.basename(pkg),
      vscode.Uri.file(path.join(wsPath, pkg))
    )
    item.canResolveChildren = true
    items.push(item)
  }
  controller.items.replace(items)
}

function populateFolderChildren(
  controller: vscode.TestController,
  folder: vscode.TestItem,
  labels: string[],
  wsPath: string
): void {
  if (folder.children.size > 0) return
  const folderPkg = folder.id.replace(/^\/\//, '')
  const directSubPkgs = new Set<string>()
  const directTargets: string[] = []
  for (const label of labels) {
    const without = label.replace(/^\/\//, '')
    const idx = without.indexOf(':')
    if (idx < 0) continue
    const pkg = without.slice(0, idx)
    if (pkg === folderPkg) {
      directTargets.push(label)
    } else if (pkg.startsWith(folderPkg + '/')) {
      const next = pkg.slice(folderPkg.length + 1).split('/')[0]
      directSubPkgs.add(`${folderPkg}/${next}`)
    }
  }
  for (const subPkg of Array.from(directSubPkgs).sort()) {
    const sub = controller.createTestItem(
      `//${subPkg}`,
      path.basename(subPkg),
      vscode.Uri.file(path.join(wsPath, subPkg))
    )
    sub.canResolveChildren = true
    folder.children.add(sub)
  }
  for (const label of directTargets.sort()) {
    const without = label.replace(/^\/\//, '')
    const colon = without.indexOf(':')
    const pkg = without.slice(0, colon)
    const name = without.slice(colon + 1)
    const buildFile = path.join(wsPath, pkg, 'BUILD')
    const targetUri = fs.existsSync(buildFile) ? vscode.Uri.file(buildFile) : undefined
    const targetItem = controller.createTestItem(label, name, targetUri)
    targetItem.canResolveChildren = true
    folder.children.add(targetItem)
  }
}

interface DiscoveredTest {
  file: string
  line: number
  name: string
  classname: string
}

export function discoverTestsForTarget(wsPath: string, target: string): DiscoveredTest[] {
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

function fileItemId(targetId: string, relPath: string): string {
  return `${targetId}::F::${relPath}`
}

function functionItemId(targetId: string, relPath: string, funcName: string): string {
  return `${fileItemId(targetId, relPath)}::${funcName}`
}

function getOrCreateFileItem(
  controller: vscode.TestController,
  targetItem: vscode.TestItem,
  wsPath: string,
  relPath: string
): vscode.TestItem {
  const id = fileItemId(targetItem.id, relPath)
  const existing = targetItem.children.get(id)
  if (existing) return existing
  const abs = path.join(wsPath, relPath)
  const uri = fs.existsSync(abs) ? vscode.Uri.file(abs) : undefined
  const fileItem = controller.createTestItem(id, path.basename(relPath), uri)
  const dir = path.dirname(relPath)
  fileItem.description = dir === '.' ? '' : dir
  targetItem.children.add(fileItem)
  return fileItem
}

function getOrCreateFunctionItem(
  controller: vscode.TestController,
  fileItem: vscode.TestItem,
  fileAbsPath: string,
  funcName: string,
  line?: number
): vscode.TestItem {
  const targetId = fileItem.id.split('::F::')[0]
  const relPath = fileItem.id.split('::F::')[1]
  const id = functionItemId(targetId, relPath, funcName)
  const existing = fileItem.children.get(id)
  if (existing) return existing
  const uri = fs.existsSync(fileAbsPath) ? vscode.Uri.file(fileAbsPath) : undefined
  const funcItem = controller.createTestItem(id, funcName, uri)
  const ln = line !== undefined ? line : findTestFunctionLine(fileAbsPath, funcName)
  if (ln !== undefined && ln >= 0) funcItem.range = new vscode.Range(ln, 0, ln, 0)
  fileItem.children.add(funcItem)
  return funcItem
}

function ensureDiscoveredChildren(
  controller: vscode.TestController,
  item: vscode.TestItem,
  wsPath: string
): void {
  if (item.children.size > 0) return
  const tests = discoverTestsForTarget(wsPath, item.id)
  const byFile = new Map<string, DiscoveredTest[]>()
  for (const t of tests) {
    const arr = byFile.get(t.file) || []
    arr.push(t)
    byFile.set(t.file, arr)
  }
  const sortedFiles = Array.from(byFile.keys()).sort()
  for (const file of sortedFiles) {
    const rel = path.relative(wsPath, file)
    const fileItem = getOrCreateFileItem(controller, item, wsPath, rel)
    for (const t of byFile.get(file)!) {
      getOrCreateFunctionItem(controller, fileItem, t.file, t.name, t.line)
    }
  }
}

interface RunUnit {
  target: vscode.TestItem
  kFilter?: string
  scopedItems?: vscode.TestItem[]
}

function classifyItem(
  item: vscode.TestItem
): 'placeholder' | 'folder' | 'target' | 'file' | 'function' {
  if (item.id.startsWith('__cmk_bazel_')) return 'placeholder'
  if (item.id.includes('::F::')) {
    const parts = item.id.split('::F::')
    return parts[1].includes('::') ? 'function' : 'file'
  }
  if (item.id.includes(':')) return 'target'
  return 'folder'
}

function findTargetAncestor(item: vscode.TestItem): vscode.TestItem | undefined {
  let cur: vscode.TestItem | undefined = item
  while (cur) {
    if (classifyItem(cur) === 'target') return cur
    cur = cur.parent
  }
  return undefined
}

function collectRunUnits(
  controller: vscode.TestController,
  request: vscode.TestRunRequest,
  populateFolder: (folder: vscode.TestItem) => void
): RunUnit[] {
  const excluded = new Set<string>()
  if (request.exclude) for (const e of request.exclude) excluded.add(e.id)

  interface Acc {
    target: vscode.TestItem
    runAll: boolean
    funcNames: Set<string>
    scopedItems: vscode.TestItem[]
  }
  const byTarget = new Map<string, Acc>()
  const get = (target: vscode.TestItem): Acc => {
    let a = byTarget.get(target.id)
    if (!a) {
      a = { target, runAll: false, funcNames: new Set(), scopedItems: [] }
      byTarget.set(target.id, a)
    }
    return a
  }

  const visit = (item: vscode.TestItem): void => {
    if (excluded.has(item.id)) return
    const kind = classifyItem(item)
    if (kind === 'placeholder') return
    if (kind === 'folder') {
      populateFolder(item)
      item.children.forEach(visit)
      return
    }
    if (kind === 'target') {
      const acc = get(item)
      acc.runAll = true
      acc.funcNames.clear()
      acc.scopedItems = []
      return
    }
    const target = findTargetAncestor(item)
    if (!target) return
    const acc = get(target)
    if (acc.runAll) return
    if (kind === 'file') {
      item.children.forEach((child) => {
        if (excluded.has(child.id)) return
        acc.funcNames.add(child.label as string)
        acc.scopedItems.push(child)
      })
    } else {
      acc.funcNames.add(item.label as string)
      acc.scopedItems.push(item)
    }
  }

  if (request.include) {
    for (const item of request.include) visit(item)
  } else {
    controller.items.forEach(visit)
  }

  const units: RunUnit[] = []
  for (const acc of byTarget.values()) {
    if (acc.runAll) {
      units.push({ target: acc.target })
    } else if (acc.funcNames.size > 0) {
      const filter = Array.from(acc.funcNames).join(' or ')
      units.push({ target: acc.target, kFilter: filter, scopedItems: acc.scopedItems })
    }
  }
  return units
}

function reportCase(run: vscode.TestRun, item: vscode.TestItem, c: JUnitTestCase): void {
  const durationMs = Math.round(c.time * 1000)
  switch (c.status) {
    case 'passed':
      run.passed(item, durationMs)
      break
    case 'skipped':
      run.skipped(item)
      break
    case 'failed':
    case 'error': {
      const text = [c.message, c.details].filter(Boolean).join('\n\n').trim() || c.status
      const msg = new vscode.TestMessage(text)
      if (item.uri && item.range) msg.location = new vscode.Location(item.uri, item.range)
      run.failed(item, [msg], durationMs)
      break
    }
  }
}

async function runOneUnit(
  controller: vscode.TestController,
  run: vscode.TestRun,
  unit: RunUnit,
  wsPath: string,
  opts: RunOptions,
  cancellation: vscode.CancellationToken
): Promise<void> {
  const item = unit.target
  const effectiveOpts: RunOptions = {
    ...opts,
    kFilter: unit.kFilter ?? opts.kFilter
  }
  run.started(item)
  if (unit.scopedItems) {
    for (const child of unit.scopedItems) run.started(child)
  }
  const args = buildBazelArgs(item.id, effectiveOpts)
  const startMs = Date.now()
  run.appendOutput(`\r\n$ bazel ${args.join(' ')}\r\n`, undefined, item)

  const child = spawn('bazel', args, { cwd: wsPath, env: spawnEnv() })
  const cancelSub = cancellation.onCancellationRequested(() => child.kill('SIGINT'))
  const onChunk = (buf: Buffer): void => {
    run.appendOutput(buf.toString().replace(/\r?\n/g, '\r\n'), undefined, item)
  }
  child.stdout.on('data', onChunk)
  child.stderr.on('data', onChunk)
  const exitCode: number = await new Promise((resolve) => {
    child.on('close', (code) => resolve(code ?? -1))
    child.on('error', () => resolve(-1))
  })
  cancelSub.dispose()
  const durationMs = Date.now() - startMs

  let cases: JUnitTestCase[] = []
  const xmlPath = targetToTestXmlPath(wsPath, item.id)
  try {
    const xml = fs.readFileSync(xmlPath, 'utf-8')
    cases = parseJunitXml(xml)
  } catch {
    /* no XML */
  }

  if (cases.length === 0) {
    if (cancellation.isCancellationRequested) {
      run.skipped(item)
      if (unit.scopedItems) for (const ci of unit.scopedItems) run.skipped(ci)
    } else if (exitCode === 0) {
      run.passed(item, durationMs)
      if (unit.scopedItems) for (const ci of unit.scopedItems) run.passed(ci)
    } else {
      const msg = new vscode.TestMessage(`bazel test exited ${exitCode}`)
      run.errored(item, msg)
      if (unit.scopedItems) for (const ci of unit.scopedItems) run.errored(ci, msg)
    }
    return
  }

  for (const c of cases) {
    const filePath =
      classnameToFilePath(wsPath, c.classname, c.file) ||
      path.join(wsPath, c.file || c.classname.replace(/\./g, '/') + '.py')
    const rel = path.relative(wsPath, filePath)
    const fileItem = getOrCreateFileItem(controller, item, wsPath, rel)
    const line = c.line !== undefined ? c.line - 1 : undefined
    const funcItem = getOrCreateFunctionItem(controller, fileItem, filePath, c.name, line)
    reportCase(run, funcItem, c)
  }

  // Roll up file-level status from its children
  item.children.forEach((fileItem) => {
    if (classifyItem(fileItem) !== 'file' || fileItem.children.size === 0) return
    const relForFile = fileItem.id.split('::F::')[1]
    const childCases = cases.filter((c) => {
      const fp =
        classnameToFilePath(wsPath, c.classname, c.file) ||
        path.join(wsPath, c.file || c.classname.replace(/\./g, '/') + '.py')
      return path.relative(wsPath, fp) === relForFile
    })
    if (childCases.length === 0) return
    const anyFailed = childCases.some((c) => c.status === 'failed' || c.status === 'error')
    const anyPassed = childCases.some((c) => c.status === 'passed')
    if (anyFailed) {
      run.failed(fileItem, [new vscode.TestMessage(`Failures in ${relForFile}`)])
    } else if (anyPassed) {
      run.passed(fileItem)
    } else {
      run.skipped(fileItem)
    }
  })

  const failed = cases.filter((c) => c.status === 'failed' || c.status === 'error').length
  if (failed > 0) {
    run.failed(item, [new vscode.TestMessage(`${failed} test(s) failed`)], durationMs)
  } else if (cases.every((c) => c.status === 'skipped')) {
    run.skipped(item)
  } else {
    run.passed(item, durationMs)
  }
}

async function runConfigurePicker(): Promise<void> {
  const cfg = vscode.workspace.getConfiguration('cmk.bazelTests')
  const editionItems = EDITIONS.map((e) => ({ label: e, picked: e === cfg.get<string>('edition') }))
  const editionPick = await vscode.window.showQuickPick(editionItems, {
    title: 'CMK ▸ Bazel Tests · Edition',
    placeHolder: 'Pick the Checkmk edition for --cmk_edition'
  })
  if (!editionPick) return
  await cfg.update('edition', editionPick.label, vscode.ConfigurationTarget.Workspace)
  notifyInfo(`CMK ▸ Bazel Tests · ${editionPick.label}`)
}

export function registerBazelTestController(): vscode.Disposable[] {
  const wsPath = getWorkspacePath()
  if (!wsPath) return []

  const disposables: vscode.Disposable[] = []
  const controller = vscode.tests.createTestController('cmk.bazelTests', 'CMK ▸ Bazel Tests')
  disposables.push(controller)

  let labelCache: string[] = []
  let triggered = false
  let pendingRefresh: Promise<void> | null = null
  const activationTime = Date.now()
  const STARTUP_WINDOW_MS = 15000
  let activeEditorChangeCount = 0

  const refresh = async (): Promise<void> => {
    try {
      labelCache = await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Window,
          title: 'CMK: Discovering Bazel test targets…'
        },
        () => discoverTargetsFromFilesystem(wsPath)
      )
      populateRootPackages(controller, labelCache, wsPath)
      log(`Bazel test discovery: ${labelCache.length} target(s)`)
    } catch (err) {
      error(`Bazel test discovery failed: ${(err as Error).message}`)
      const failure = controller.createTestItem(
        '__cmk_bazel_error__',
        'Bazel test discovery failed'
      )
      failure.description = (err as Error).message
      controller.items.replace([failure])
      notifyError('CMK: Bazel test discovery failed', (err as Error).message)
    }
  }

  const triggerDiscovery = (reason: string): Promise<void> => {
    if (triggered) return pendingRefresh ?? Promise.resolve()
    triggered = true
    log(`Bazel test discovery triggered: ${reason}`)
    pendingRefresh = refresh()
    return pendingRefresh
  }

  const showHint = (): void => {
    const hint = controller.createTestItem(
      '__cmk_bazel_hint__',
      'Open a Python test file or click ↻ to discover Bazel tests'
    )
    hint.description = 'tests not yet discovered'
    controller.items.replace([hint])
  }
  showHint()

  controller.resolveHandler = async (item) => {
    if (!item) return
    if (item.children.size > 0) return
    const kind = classifyItem(item)
    if (kind === 'placeholder') return
    item.busy = true
    try {
      await new Promise<void>((resolve) => setImmediate(resolve))
      if (kind === 'folder') {
        populateFolderChildren(controller, item, labelCache, wsPath)
      } else if (kind === 'target') {
        ensureDiscoveredChildren(controller, item, wsPath)
      }
    } catch (err) {
      error(`Bazel test discovery for ${item.id} failed: ${(err as Error).message}`)
    } finally {
      item.busy = false
    }
  }

  controller.refreshHandler = async () => {
    triggered = true
    pendingRefresh = refresh()
    await pendingRefresh
  }

  const onDemand =
    vscode.workspace.getConfiguration('cmk.bazelTests').get<boolean>('onDemand') ?? true
  if (!onDemand) {
    void triggerDiscovery('eager discovery (cmk.bazelTests.onDemand=false)')
  } else {
    const PYTHON_TEST_FILE = /(?:^|\/)test_[^/]+\.py$|_test\.py$|\/tests?\//
    const matchesTestFile = (doc: vscode.TextDocument): boolean =>
      doc.languageId === 'python' &&
      doc.uri.scheme === 'file' &&
      PYTHON_TEST_FILE.test(doc.uri.fsPath)
    disposables.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        activeEditorChangeCount++
        if (Date.now() - activationTime < STARTUP_WINDOW_MS) return
        if (activeEditorChangeCount < 2) return
        if (!editor) return
        if (matchesTestFile(editor.document)) void triggerDiscovery('test file focused')
      })
    )
  }

  // Debounced re-discovery on BUILD changes — only after first trigger
  const watcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(wsPath, 'tests/**/BUILD')
  )
  let timer: NodeJS.Timeout | null = null
  const debounced = (): void => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      if (triggered) refresh().catch(() => {})
    }, 5000)
  }
  watcher.onDidCreate(debounced)
  watcher.onDidDelete(debounced)
  watcher.onDidChange(debounced)
  disposables.push(watcher)
  disposables.push({
    dispose: () => {
      if (timer) clearTimeout(timer)
    }
  })

  const populateFolder = (folder: vscode.TestItem): void => {
    if (folder.children.size === 0) {
      populateFolderChildren(controller, folder, labelCache, wsPath)
    }
  }

  const runHandler = async (
    request: vscode.TestRunRequest,
    cancellation: vscode.CancellationToken,
    promptForK: boolean
  ): Promise<void> => {
    const opts = getRunOptions()
    if (promptForK) {
      const k = await vscode.window.showInputBox({
        prompt: 'pytest -k expression',
        placeHolder: 'e.g. test_login or "auth and not slow"'
      })
      if (k === undefined) return
      opts.kFilter = k
    }
    if (!triggered) await triggerDiscovery('test run requested')
    const units = collectRunUnits(controller, request, populateFolder)
    if (units.length === 0) {
      notifyInfo('CMK: No Bazel test targets selected')
      return
    }
    const run = controller.createTestRun(request)
    try {
      for (const unit of units) {
        if (cancellation.isCancellationRequested) {
          run.skipped(unit.target)
          continue
        }
        await runOneUnit(controller, run, unit, wsPath, opts, cancellation)
      }
    } finally {
      run.end()
    }
  }

  controller.createRunProfile(
    'Run',
    vscode.TestRunProfileKind.Run,
    (request, token) => {
      runHandler(request, token, false).catch((err) =>
        error(`Bazel test run failed: ${(err as Error).message}`)
      )
    },
    true
  )
  controller.createRunProfile(
    'Run with -k…',
    vscode.TestRunProfileKind.Run,
    (request, token) => {
      runHandler(request, token, true).catch((err) =>
        error(`Bazel test run failed: ${(err as Error).message}`)
      )
    },
    false
  )

  disposables.push(
    vscode.commands.registerCommand('cmk.bazelTests.configure', () => runConfigurePicker())
  )
  disposables.push(vscode.commands.registerCommand('cmk.bazelTests.refresh', () => refresh()))

  return disposables
}
