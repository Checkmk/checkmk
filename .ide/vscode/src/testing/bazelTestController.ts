/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { spawn } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { availableEditions, effectiveEdition } from '../core/editions'
import { error, log, notifyError, notifyInfo } from '../core/log'
import {
  DISCOVERY_ROOTS,
  discoverTargetsFromFilesystem,
  populateFolderChildren,
  populateRootPackages
} from './discovery'
import { parseJunitXml } from './junit'
import { spawnEnv, targetToTestXmlPath } from './process'
import {
  buildCcArgs,
  ccFullNameFromItemId,
  ensureCcDiscovered,
  reportCcTestRun
} from './runners/cc'
import { discoverPyDocTestsForTarget, reportPyDocTestRun } from './runners/pydoctest'
import {
  buildPyTestArgs,
  discoverPyTestsForTarget,
  findPyTestLine,
  pyCaseFilePath
} from './runners/pytest'
import {
  buildRustArgs,
  ensureRustDiscovered,
  reportRustTestRun,
  rustFullNameFromItemId
} from './runners/rust'
import {
  VITEST_FILE_REGEX,
  buildVitestArgs,
  discoverVitestTestsForTarget,
  findVitestTestLine,
  vitestCaseFilePath,
  vitestCaseLeafName
} from './runners/vitest'
import {
  classifyItem,
  findTargetAncestor,
  getOrCreateFileItem,
  getOrCreateFunctionItem,
  getOrCreateSyntheticFolderChain
} from './tree'
import type {
  DiscoveredTarget,
  DiscoveredTest,
  JUnitTestCase,
  RuleKind,
  RuleScope,
  RunOptions
} from './types'

// Re-exports kept for backward compatibility with the existing test file.
export { parseJunitXml } from './junit'
export type { JUnitTestCase, RuleKind, DiscoveredTarget } from './types'
export { discoverPyTestsForTarget as discoverTestsForTarget } from './runners/pytest'
export { discoverVitestTestsForTarget } from './runners/vitest'
export { discoverPyDocTestsForTarget } from './runners/pydoctest'
export { parseRustTestsFromFile, parseLibtestOutput } from './runners/rust'
export { extractSystemOut as extractRustLibtestOutput } from './junit'
export { discoverTargetsFromFilesystem }

function getWorkspacePath(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

function getRunOptions(): RunOptions {
  return {
    edition: effectiveEdition()
  }
}

function buildBazelArgs(target: string, opts: RunOptions, scope: RuleScope): string[] {
  const args = [
    'test',
    target,
    `--cmk_edition=${opts.edition}`,
    '--test_output=streamed',
    '--test_summary=detailed'
  ]
  switch (scope.kind) {
    case 'py_test':
      args.push(...buildPyTestArgs(opts))
      break
    case 'vitest_test':
      args.push(...buildVitestArgs(opts, scope))
      break
    case 'rust_test':
      args.push(...buildRustArgs(scope))
      break
    case 'cc_test':
      args.push(...buildCcArgs(scope))
      break
    case 'py_doc_test':
      // No scoping: doctest runs the whole module suite.
      break
  }
  return args
}

function ensureDiscoveredChildren(
  controller: vscode.TestController,
  item: vscode.TestItem,
  wsPath: string,
  kind: RuleKind
): void {
  if (item.children.size > 0) return
  let tests: DiscoveredTest[]
  switch (kind) {
    case 'vitest_test':
      tests = discoverVitestTestsForTarget(wsPath, item.id)
      break
    case 'py_test':
      tests = discoverPyTestsForTarget(wsPath, item.id)
      break
    case 'py_doc_test':
      tests = discoverPyDocTestsForTarget(wsPath, item.id)
      break
    default:
      return
  }
  if (tests.length === 0) return
  const byFile = new Map<string, DiscoveredTest[]>()
  for (const t of tests) {
    const arr = byFile.get(t.file) || []
    arr.push(t)
    byFile.set(t.file, arr)
  }
  const sortedFiles = Array.from(byFile.keys()).sort()
  for (const file of sortedFiles) {
    const rel = path.relative(wsPath, file)
    const parent = getOrCreateSyntheticFolderChain(controller, item, wsPath, rel, kind)
    const fileItem = getOrCreateFileItem(controller, item, parent, wsPath, rel)
    const findLine = kind === 'vitest_test' ? findVitestTestLine : findPyTestLine
    for (const t of byFile.get(file)!) {
      getOrCreateFunctionItem(controller, fileItem, t.file, t.name, t.line, findLine)
    }
  }
}

interface RunUnit {
  target: vscode.TestItem
  kind: RuleKind
  kFilter?: string
  scopedFilesRel?: string[]
  scopedTestNames?: string[]
  scopedItems?: vscode.TestItem[]
}

function collectRunUnits(
  controller: vscode.TestController,
  request: vscode.TestRunRequest,
  populateFolder: (folder: vscode.TestItem) => void,
  kindByLabel: Map<string, RuleKind>
): RunUnit[] {
  const excluded = new Set<string>()
  if (request.exclude) for (const e of request.exclude) excluded.add(e.id)

  interface Acc {
    target: vscode.TestItem
    runAll: boolean
    funcNames: Set<string>
    fileItems: Set<vscode.TestItem>
    scopedItems: vscode.TestItem[]
  }
  const byTarget = new Map<string, Acc>()
  const get = (target: vscode.TestItem): Acc => {
    let a = byTarget.get(target.id)
    if (!a) {
      a = {
        target,
        runAll: false,
        funcNames: new Set(),
        fileItems: new Set(),
        scopedItems: []
      }
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
      acc.fileItems.clear()
      acc.scopedItems = []
      return
    }
    const target = findTargetAncestor(item)
    if (!target) return
    const acc = get(target)
    if (acc.runAll) return
    const tk = kindByLabel.get(target.id)
    const nameOf = (it: vscode.TestItem): string => {
      if (tk === 'rust_test') {
        const full = rustFullNameFromItemId(target.id, it.id)
        if (full) return full
      } else if (tk === 'cc_test') {
        const full = ccFullNameFromItemId(target.id, it.id)
        if (full) return full
      }
      return it.label as string
    }
    if (kind === 'file') {
      acc.fileItems.add(item)
      item.children.forEach((child) => {
        if (excluded.has(child.id)) return
        acc.funcNames.add(nameOf(child))
        acc.scopedItems.push(child)
      })
    } else {
      acc.funcNames.add(nameOf(item))
      acc.scopedItems.push(item)
      if (item.parent) acc.fileItems.add(item.parent)
    }
  }

  if (request.include) {
    for (const item of request.include) visit(item)
  } else {
    controller.items.forEach(visit)
  }

  const units: RunUnit[] = []
  for (const acc of byTarget.values()) {
    const targetKind = kindByLabel.get(acc.target.id) ?? 'py_test'
    if (acc.runAll) {
      units.push({ target: acc.target, kind: targetKind })
      continue
    }
    if (acc.funcNames.size === 0) continue

    if (targetKind === 'py_test') {
      const filter = Array.from(acc.funcNames).join(' or ')
      units.push({
        target: acc.target,
        kind: 'py_test',
        kFilter: filter,
        scopedItems: acc.scopedItems
      })
    } else if (targetKind === 'vitest_test') {
      const targetPkg = acc.target.id.replace(/^\/\//, '').split(':')[0]
      const filesRel = Array.from(acc.fileItems)
        .map((fi) => fi.id.split('::F::')[1])
        .filter((rel) => rel && rel.startsWith(targetPkg + '/'))
        .map((rel) => rel.slice(targetPkg.length + 1))
      const onlyWholeFiles = acc.scopedItems.every((si) => classifyItem(si) === 'file')
      const names = onlyWholeFiles ? [] : Array.from(acc.funcNames)
      units.push({
        target: acc.target,
        kind: 'vitest_test',
        scopedFilesRel: filesRel,
        scopedTestNames: names,
        scopedItems: acc.scopedItems
      })
    } else if (targetKind === 'rust_test') {
      units.push({
        target: acc.target,
        kind: 'rust_test',
        scopedTestNames: Array.from(acc.funcNames),
        scopedItems: acc.scopedItems
      })
    } else if (targetKind === 'cc_test') {
      units.push({
        target: acc.target,
        kind: 'cc_test',
        scopedTestNames: Array.from(acc.funcNames),
        scopedItems: acc.scopedItems
      })
    } else {
      units.push({ target: acc.target, kind: targetKind, scopedItems: acc.scopedItems })
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

function caseFilePath(
  wsPath: string,
  c: JUnitTestCase,
  kind: RuleKind,
  targetPkg?: string
): string {
  if (kind === 'vitest_test') return vitestCaseFilePath(wsPath, c, targetPkg)
  return pyCaseFilePath(wsPath, c, targetPkg)
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
  const args = buildBazelArgs(item.id, effectiveOpts, {
    kind: unit.kind,
    scopedFilesRel: unit.scopedFilesRel,
    scopedTestNames: unit.scopedTestNames
  })
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
  let xmlContent = ''
  const xmlPath = targetToTestXmlPath(wsPath, item.id)
  try {
    xmlContent = fs.readFileSync(xmlPath, 'utf-8')
    cases = parseJunitXml(xmlContent)
  } catch {
    /* no XML */
  }

  const cancelled = cancellation.isCancellationRequested

  if (unit.kind === 'rust_test') {
    reportRustTestRun({
      controller,
      run,
      item,
      wsPath,
      durationMs,
      exitCode,
      cancelled,
      xmlContent,
      reportCase: (it, c) => reportCase(run, it, c),
      scopedItems: unit.scopedItems
    })
    return
  }

  if (unit.kind === 'cc_test') {
    reportCcTestRun({
      controller,
      run,
      item,
      wsPath,
      durationMs,
      exitCode,
      cancelled,
      cases,
      reportCase: (it, c) => reportCase(run, it, c),
      scopedItems: unit.scopedItems
    })
    return
  }

  if (unit.kind === 'py_doc_test') {
    reportPyDocTestRun({
      run,
      item,
      durationMs,
      exitCode,
      cancelled,
      scopedItems: unit.scopedItems
    })
    return
  }

  if (cases.length === 0) {
    if (cancelled) {
      run.skipped(item)
    } else if (exitCode === 0) {
      run.passed(item, durationMs)
      if (unit.scopedItems) for (const ci of unit.scopedItems) run.passed(ci)
    } else {
      const msg = new vscode.TestMessage(`bazel test exited ${exitCode}`)
      run.failed(item, [msg], durationMs)
      if (unit.scopedItems) for (const ci of unit.scopedItems) run.failed(ci, [msg])
    }
    return
  }

  const targetPkg = item.id.replace(/^\/\//, '').split(':')[0]
  const findLine = unit.kind === 'vitest_test' ? findVitestTestLine : findPyTestLine
  for (const c of cases) {
    const filePath = caseFilePath(wsPath, c, unit.kind, targetPkg)
    const rel = path.relative(wsPath, filePath)
    const parent = getOrCreateSyntheticFolderChain(controller, item, wsPath, rel, unit.kind)
    const fileItem = getOrCreateFileItem(controller, item, parent, wsPath, rel)
    const line = c.line !== undefined ? c.line - 1 : undefined
    // Vitest emits "describe > it" as the case name; discovery captured only
    // the it-name. Use the leaf so cases merge into the discovered items
    // instead of appearing as duplicate siblings.
    const funcName = unit.kind === 'vitest_test' ? vitestCaseLeafName(c.name) : c.name
    const funcItem = getOrCreateFunctionItem(
      controller,
      fileItem,
      filePath,
      funcName,
      line,
      findLine
    )
    reportCase(run, funcItem, c)
  }

  // Roll up file-level status from its children (recurse through any synth folders).
  const rollupFile = (fileItem: vscode.TestItem): void => {
    if (fileItem.children.size === 0) return
    const relForFile = fileItem.id.split('::F::')[1]
    const childCases = cases.filter(
      (c) => path.relative(wsPath, caseFilePath(wsPath, c, unit.kind, targetPkg)) === relForFile
    )
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
  }
  const walkForRollup = (node: vscode.TestItem): void => {
    node.children.forEach((child) => {
      const ck = classifyItem(child)
      if (ck === 'file') rollupFile(child)
      else if (ck === 'folder') walkForRollup(child)
    })
  }
  walkForRollup(item)

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
  const editions = availableEditions()
  if (editions.length === 1) {
    notifyInfo(`CMK Tests · ${editions[0]} (only edition available in this checkout)`)
    return
  }
  const current = effectiveEdition()
  const editionItems = editions.map((e) => ({ label: e, picked: e === current }))
  const editionPick = await vscode.window.showQuickPick(editionItems, {
    title: 'CMK Tests · Edition',
    placeHolder: 'Pick the Checkmk edition for --cmk_edition'
  })
  if (!editionPick) return
  await cfg.update('edition', editionPick.label, vscode.ConfigurationTarget.Workspace)
  notifyInfo(`CMK Tests · ${editionPick.label}`)
}

export function registerBazelTestController(): vscode.Disposable[] {
  const wsPath = getWorkspacePath()
  if (!wsPath) return []

  const disposables: vscode.Disposable[] = []
  const controller = vscode.tests.createTestController('cmk.bazelTests', 'CMK Tests')
  disposables.push(controller)

  let labelCache: DiscoveredTarget[] = []
  const kindByLabel = new Map<string, RuleKind>()
  let triggered = false
  let pendingRefresh: Promise<void> | null = null
  const activationTime = Date.now()
  const STARTUP_WINDOW_MS = 15000
  let activeEditorChangeCount = 0

  const showDiscovering = (): void => {
    const item = controller.createTestItem(
      '__cmk_bazel_discovering__',
      'Discovering Bazel test targets…'
    )
    item.busy = true
    controller.items.replace([item])
  }

  const refresh = async (): Promise<void> => {
    showDiscovering()
    try {
      labelCache = await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Window,
          title: 'CMK: Discovering Bazel test targets…'
        },
        () => discoverTargetsFromFilesystem(wsPath)
      )
      kindByLabel.clear()
      for (const t of labelCache) kindByLabel.set(t.label, t.kind)
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

  let buildWatchersSetUp = false
  let watcherDebounceTimer: NodeJS.Timeout | null = null
  const setUpBuildWatchers = (): void => {
    if (buildWatchersSetUp) return
    buildWatchersSetUp = true
    const watchers = DISCOVERY_ROOTS.map((root) =>
      vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(wsPath, `${root}/**/BUILD`)
      )
    )
    const debounced = (): void => {
      if (watcherDebounceTimer) clearTimeout(watcherDebounceTimer)
      watcherDebounceTimer = setTimeout(() => {
        refresh().catch(() => {})
      }, 5000)
    }
    for (const w of watchers) {
      w.onDidCreate(debounced)
      w.onDidDelete(debounced)
      w.onDidChange(debounced)
      disposables.push(w)
    }
  }

  const triggerDiscovery = (reason: string): Promise<void> => {
    if (triggered) return pendingRefresh ?? Promise.resolve()
    triggered = true
    log(`Bazel test discovery triggered: ${reason}`)
    pendingRefresh = refresh()
    setUpBuildWatchers()
    return pendingRefresh
  }

  const showHint = (): void => {
    const hint = controller.createTestItem(
      '__cmk_bazel_hint__',
      'Open a test file or click ↻ to discover Bazel tests'
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
        if (item.id.includes('::D::')) {
          let cur: vscode.TestItem | undefined = item
          while (cur && classifyItem(cur) !== 'target') cur = cur.parent
          if (cur) {
            const tk = kindByLabel.get(cur.id) ?? 'py_test'
            ensureDiscoveredChildren(controller, cur, wsPath, tk)
          }
        } else {
          populateFolderChildren(controller, item, labelCache, wsPath, kindByLabel)
        }
      } else if (kind === 'target') {
        const targetKind = kindByLabel.get(item.id) ?? 'py_test'
        if (targetKind === 'rust_test') {
          await ensureRustDiscovered(controller, item, wsPath)
        } else if (targetKind === 'cc_test') {
          await ensureCcDiscovered(controller, item, wsPath)
        } else {
          ensureDiscoveredChildren(controller, item, wsPath, targetKind)
        }
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
    const RUST_FILE = /\.rs$/
    const CC_FILE = /\.(cc|cpp|cxx)$/
    const isUnderDiscoveryRoot = (fsPath: string): boolean => {
      const rel = path.relative(wsPath, fsPath)
      if (rel.startsWith('..')) return false
      return DISCOVERY_ROOTS.some((r) => rel === r || rel.startsWith(r + path.sep))
    }
    const matchesTestFile = (doc: vscode.TextDocument): boolean => {
      if (doc.uri.scheme !== 'file') return false
      const fsPath = doc.uri.fsPath
      if (doc.languageId === 'python' && PYTHON_TEST_FILE.test(fsPath)) return true
      if (VITEST_FILE_REGEX.test(fsPath)) return true
      if ((RUST_FILE.test(fsPath) || CC_FILE.test(fsPath)) && isUnderDiscoveryRoot(fsPath)) {
        return true
      }
      return false
    }
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

  disposables.push({
    dispose: () => {
      if (watcherDebounceTimer) clearTimeout(watcherDebounceTimer)
    }
  })

  const populateFolder = (folder: vscode.TestItem): void => {
    if (folder.children.size > 0) return
    if (folder.id.includes('::D::')) {
      let cur: vscode.TestItem | undefined = folder
      while (cur && classifyItem(cur) !== 'target') cur = cur.parent
      if (cur) {
        const tk = kindByLabel.get(cur.id) ?? 'py_test'
        ensureDiscoveredChildren(controller, cur, wsPath, tk)
      }
      return
    }
    populateFolderChildren(controller, folder, labelCache, wsPath, kindByLabel)
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
    const units = collectRunUnits(controller, request, populateFolder, kindByLabel)
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
