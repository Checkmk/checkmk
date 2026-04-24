/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as path from 'path'
import * as vscode from 'vscode'

import { error, log, notifyInfo } from '../../core/log'
import {
  applyDynamicMypyTargets,
  discoverMypyTargets,
  resolveTargetForFile,
  setMypyTargetsFilter
} from './mypyConfig'

const STATE_KEY = 'cmk.mypy.activeTargets'
const SETTING_ENABLED = 'dynamicTargets.enabled'
const SETTING_BASELINE = 'dynamicTargets.baseline'
const APPLY_DEBOUNCE_MS = 1500

export const ALWAYS_ON_TARGETS = ['cmk']

let activeTargets = new Set<string>()
const stagedActiveAdd = new Set<string>()
const stagedActiveRemove = new Set<string>()
const stagedBaselineAdd = new Set<string>()
const stagedBaselineRemove = new Set<string>()
let lastAppliedSignature = ''

function clearStagedAll(): void {
  stagedActiveAdd.clear()
  stagedActiveRemove.clear()
  stagedBaselineAdd.clear()
  stagedBaselineRemove.clear()
}

function anyStaged(): boolean {
  return (
    stagedActiveAdd.size +
      stagedActiveRemove.size +
      stagedBaselineAdd.size +
      stagedBaselineRemove.size >
    0
  )
}

function stagedTargetUnion(): string[] {
  const s = new Set<string>()
  for (const t of stagedActiveAdd) s.add(t)
  for (const t of stagedActiveRemove) s.add(t)
  for (const t of stagedBaselineAdd) s.add(t)
  for (const t of stagedBaselineRemove) s.add(t)
  return [...s].sort()
}
let pendingApply: NodeJS.Timeout | null = null
let pendingWsPath: string | null = null
let extContext: vscode.ExtensionContext | null = null
const promptedTargets = new Set<string>()

function isEnabled(): boolean {
  return vscode.workspace.getConfiguration('cmk.mypy').get<boolean>(SETTING_ENABLED, false)
}

function getBaselineSetting(): string[] {
  return vscode.workspace.getConfiguration('cmk.mypy').get<string[]>(SETTING_BASELINE, [])
}

function toRelPath(wsPath: string, abs: string): string | null {
  const rel = path.relative(wsPath, abs)
  if (rel.startsWith('..') || path.isAbsolute(rel)) return null
  return rel.split(path.sep).join('/')
}

function baselineTargets(catalog: string[]): Set<string> {
  const targets = new Set<string>()
  for (const t of ALWAYS_ON_TARGETS) {
    if (catalog.includes(t)) targets.add(t)
  }
  for (const t of getBaselineSetting()) {
    if (catalog.includes(t)) targets.add(t)
  }
  return targets
}

function scheduleApply(wsPath: string): void {
  pendingWsPath = wsPath
  if (pendingApply) clearTimeout(pendingApply)
  pendingApply = setTimeout(() => {
    pendingApply = null
    const ws = pendingWsPath
    pendingWsPath = null
    if (!ws) return
    persistAndApply(ws).catch((err) =>
      error(`Dynamic mypy targets apply failed: ${(err as Error).message}`)
    )
  }, APPLY_DEBOUNCE_MS)
}

async function persistAndApply(wsPath: string): Promise<void> {
  const sorted = [...activeTargets].sort()
  const signature = sorted.join('\n')
  if (signature === lastAppliedSignature) {
    log('Dynamic mypy targets: active set unchanged, skipping write')
    return
  }
  if (extContext) await extContext.workspaceState.update(STATE_KEY, sorted)
  await applyDynamicMypyTargets(wsPath, sorted)
  lastAppliedSignature = signature
  log(`Dynamic mypy targets: ${sorted.length} active`)
}

function onDocOpened(wsPath: string, doc: vscode.TextDocument): void {
  if (!isEnabled()) return
  if (doc.languageId !== 'python') return
  if (doc.uri.scheme !== 'file') return
  const rel = toRelPath(wsPath, doc.uri.fsPath)
  if (!rel) return
  const catalog = discoverMypyTargets(wsPath)
  const target = resolveTargetForFile(rel, catalog)
  if (!target) return
  if (activeTargets.has(target)) return
  if (promptedTargets.has(target)) return
  promptedTargets.add(target)
  const STAGE = 'Stage'
  const ACTIVATE = 'Activate Now'
  const BASELINE = 'Add to Baseline'
  vscode.window
    .showInformationMessage(
      `Mypy: "${target}" is not in the active targets.`,
      { detail: `Opened ${rel}` },
      STAGE,
      ACTIVATE,
      BASELINE
    )
    .then((choice) => {
      if (choice === STAGE) {
        stagedActiveAdd.add(target)
        stagedActiveRemove.delete(target)
        log(`Dynamic mypy targets: staged add "${target}" (user)`)
        vscode.commands.executeCommand('cmk.dashboard.refresh.ideHealth')
      } else if (choice === ACTIVATE) {
        activeTargets.add(target)
        stagedActiveAdd.delete(target)
        stagedActiveRemove.delete(target)
        log(`Dynamic mypy targets: activated "${target}" (user)`)
        scheduleApply(wsPath)
        vscode.commands.executeCommand('cmk.dashboard.refresh.ideHealth')
      } else if (choice === BASELINE) {
        activeTargets.add(target)
        stagedActiveAdd.delete(target)
        stagedActiveRemove.delete(target)
        stagedBaselineAdd.delete(target)
        const current = getBaselineSetting()
        if (!current.includes(target)) {
          vscode.workspace
            .getConfiguration('cmk.mypy')
            .update(SETTING_BASELINE, [...current, target], vscode.ConfigurationTarget.Workspace)
            .then(undefined, (err) =>
              error(`Failed to persist baseline: ${(err as Error).message}`)
            )
        }
        log(`Dynamic mypy targets: added "${target}" to baseline (user)`)
        scheduleApply(wsPath)
        vscode.commands.executeCommand('cmk.dashboard.refresh.ideHealth')
      } else {
        // Dismissed — keep promptedTargets entry so we don't re-ask this session
      }
    })
}

export function registerDynamicMypyTargets(context: vscode.ExtensionContext): vscode.Disposable[] {
  extContext = context
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return []

  const disposables: vscode.Disposable[] = []

  const installFilterIfEnabled = (): void => {
    if (!isEnabled()) {
      setMypyTargetsFilter(null)
      return
    }
    const catalog = discoverMypyTargets(wsPath)
    // Always reset to always-on + baseline on activation. In-session activations
    // still persist to STATE_KEY for the ideHealth view, but are discarded on
    // reload so a new window starts with a predictable, minimal target set.
    activeTargets = baselineTargets(catalog)
    setMypyTargetsFilter((full) =>
      activeTargets.size === 0 ? full : full.filter((t) => activeTargets.has(t))
    )
  }

  const applyEnabledState = async (): Promise<void> => {
    installFilterIfEnabled()
    if (!isEnabled()) {
      await applyDynamicMypyTargets(wsPath)
      return
    }
    await persistAndApply(wsPath)
  }

  installFilterIfEnabled()
  applyEnabledState().catch((err) =>
    error(`Dynamic mypy targets init failed: ${(err as Error).message}`)
  )

  disposables.push(
    vscode.workspace.onDidOpenTextDocument((doc) => onDocOpened(wsPath, doc)),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration(`cmk.mypy.${SETTING_ENABLED}`)) {
        applyEnabledState().catch((err) =>
          error(`Dynamic mypy targets reconfigure failed: ${(err as Error).message}`)
        )
      } else if (e.affectsConfiguration(`cmk.mypy.${SETTING_BASELINE}`) && isEnabled()) {
        const catalog = discoverMypyTargets(wsPath)
        for (const t of baselineTargets(catalog)) activeTargets.add(t)
        scheduleApply(wsPath)
      }
    }),
    vscode.commands.registerCommand('cmk.mypy.resetTargetsToBaseline', async () => {
      if (!isEnabled()) {
        notifyInfo('CMK ▸ Mypy: Dynamic targets not enabled (cmk.mypy.dynamicTargets.enabled)')
        return
      }
      const catalog = discoverMypyTargets(wsPath)
      activeTargets = baselineTargets(catalog)
      clearStagedAll()
      promptedTargets.clear()
      await persistAndApply(wsPath)
      notifyInfo(`CMK ▸ Mypy: Applied baseline (${activeTargets.size} targets)`)
    }),
    vscode.commands.registerCommand('cmk.mypy.applyStagedTargets', async () => {
      if (!anyStaged()) {
        notifyInfo('CMK ▸ Mypy: No staged changes')
        return
      }
      const changedCount = stagedTargetUnion().length
      for (const t of stagedActiveAdd) activeTargets.add(t)
      for (const t of stagedActiveRemove) {
        if (!ALWAYS_ON_TARGETS.includes(t)) activeTargets.delete(t)
      }
      const baselineNeedsWrite = stagedBaselineAdd.size > 0 || stagedBaselineRemove.size > 0
      if (baselineNeedsWrite) {
        const current = new Set(getBaselineSetting())
        for (const t of stagedBaselineAdd) current.add(t)
        for (const t of stagedBaselineRemove) {
          if (!ALWAYS_ON_TARGETS.includes(t)) current.delete(t)
        }
        await writeBaseline([...current].sort())
      }
      clearStagedAll()
      await persistAndApply(wsPath)
      notifyInfo(`CMK ▸ Mypy: Applied ${changedCount} staged change(s)`)
      vscode.commands.executeCommand('cmk.dashboard.refresh.ideHealth')
    }),
    vscode.commands.registerCommand('cmk.mypy.discardStagedTargets', async () => {
      if (!anyStaged()) return
      const count = stagedTargetUnion().length
      clearStagedAll()
      notifyInfo(`CMK ▸ Mypy: Discarded ${count} staged change(s)`)
      vscode.commands.executeCommand('cmk.dashboard.refresh.ideHealth')
    }),
    vscode.commands.registerCommand('cmk.mypy.activateTargetPick', async () => {
      if (!isEnabled()) {
        notifyInfo('CMK ▸ Mypy: Dynamic targets not enabled (cmk.mypy.dynamicTargets.enabled)')
        return
      }
      const catalog = discoverMypyTargets(wsPath)
      const inactive = catalog.filter((t) => !activeTargets.has(t)).sort()
      if (inactive.length === 0) {
        notifyInfo('CMK ▸ Mypy: All targets are already active')
        return
      }
      const picked = await vscode.window.showQuickPick(inactive, {
        canPickMany: true,
        placeHolder: 'Select targets to activate',
        title: `Mypy targets — ${inactive.length} inactive`
      })
      if (!picked || picked.length === 0) return
      for (const t of picked) {
        if (catalog.includes(t) && !activeTargets.has(t)) {
          activeTargets.add(t)
          stagedActiveAdd.delete(t)
          stagedActiveRemove.delete(t)
          promptedTargets.delete(t)
        }
      }
      scheduleApply(wsPath)
      notifyInfo(`CMK ▸ Mypy: Activated ${picked.length} target(s)`)
    }),
    {
      dispose: () => {
        if (pendingApply) clearTimeout(pendingApply)
        pendingApply = null
        setMypyTargetsFilter(null)
      }
    }
  )

  return disposables
}

export function getActiveTargetCount(): number {
  return activeTargets.size
}

export function getMypyTargetsSnapshot(wsPath: string | undefined): {
  enabled: boolean
  activeCount: number
  catalogSize: number
  activeTargets: string[]
  baselineTargets: string[]
  alwaysOnTargets: string[]
  stagedActiveAdd: string[]
  stagedActiveRemove: string[]
  stagedBaselineAdd: string[]
  stagedBaselineRemove: string[]
  catalog: string[]
} {
  const catalog = wsPath ? discoverMypyTargets(wsPath) : []
  return {
    enabled: isEnabled(),
    activeCount: activeTargets.size,
    catalogSize: catalog.length,
    activeTargets: [...activeTargets].sort(),
    baselineTargets: [...getBaselineSetting()].sort(),
    alwaysOnTargets: [...ALWAYS_ON_TARGETS],
    stagedActiveAdd: [...stagedActiveAdd].sort(),
    stagedActiveRemove: [...stagedActiveRemove].sort(),
    stagedBaselineAdd: [...stagedBaselineAdd].sort(),
    stagedBaselineRemove: [...stagedBaselineRemove].sort(),
    catalog: [...catalog].sort()
  }
}

export function activateTarget(target: string): void {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return
  const catalog = discoverMypyTargets(wsPath)
  if (!catalog.includes(target)) return
  if (stagedActiveRemove.delete(target)) return
  if (activeTargets.has(target)) return
  stagedActiveAdd.add(target)
  promptedTargets.delete(target)
}

export function deactivateTarget(target: string): void {
  if (ALWAYS_ON_TARGETS.includes(target)) return
  if (stagedActiveAdd.delete(target)) return
  if (!activeTargets.has(target)) return
  stagedActiveRemove.add(target)
}

async function writeBaseline(next: string[]): Promise<void> {
  await vscode.workspace
    .getConfiguration('cmk.mypy')
    .update(SETTING_BASELINE, next, vscode.ConfigurationTarget.Workspace)
}

export function addTargetToBaseline(target: string): void {
  if (ALWAYS_ON_TARGETS.includes(target)) return
  if (stagedBaselineRemove.delete(target)) return
  const current = getBaselineSetting()
  if (!current.includes(target)) stagedBaselineAdd.add(target)
  if (!activeTargets.has(target)) stagedActiveAdd.add(target)
  stagedActiveRemove.delete(target)
}

export function removeTargetFromBaseline(target: string): void {
  if (ALWAYS_ON_TARGETS.includes(target)) return
  if (stagedBaselineAdd.delete(target)) return
  const current = getBaselineSetting()
  if (current.includes(target)) stagedBaselineRemove.add(target)
}
