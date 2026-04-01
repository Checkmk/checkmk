/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { execSync } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import * as profileManager from '../profiles/profileManager'

export interface BuildTarget {
  ok: boolean
  label: string
  commandId: string
}

export type BuildStatus = Record<string, BuildTarget>

export interface CommandEntry {
  name: string
  command: string
  requires?: string
  postAction?: string
}

export function checkBuildStatus(wsPath: string): BuildStatus {
  const status: BuildStatus = {
    venv: { ok: false, label: 'Python venv', commandId: 'cmk.buildVenv' },
    sharedTypingTs: { ok: false, label: 'shared-typing (TS)', commandId: 'cmk.buildSharedTyping' },
    sharedTypingPy: { ok: false, label: 'shared-typing (PY)', commandId: 'cmk.buildVenv' },
    cmkFrontend: { ok: false, label: 'cmk-frontend', commandId: 'cmk.buildCmkFrontend' },
    mypyConfig: { ok: false, label: 'mypy config', commandId: 'cmk.regenerateMypyConfig' },
    prettierConfig: {
      ok: false,
      label: 'prettier config',
      commandId: 'cmk.regeneratePrettierConfig'
    }
  }

  const venvCfg = path.join(wsPath, '.venv', 'pyvenv.cfg')
  status.venv.ok = fs.existsSync(venvCfg)

  const sharedTypingLink = path.join(
    wsPath,
    'packages',
    'cmk-frontend-vue',
    'node_modules',
    'cmk-shared-typing'
  )
  try {
    const target = fs.readlinkSync(sharedTypingLink)
    const resolved = path.resolve(path.dirname(sharedTypingLink), target)
    status.sharedTypingTs.ok = fs.existsSync(resolved)
  } catch {
    status.sharedTypingTs.ok = false
  }

  try {
    const sitePackages = fs
      .readdirSync(path.join(wsPath, '.venv', 'lib'))
      .filter((d) => d.startsWith('python'))
      .map((d) =>
        path.join(wsPath, '.venv', 'lib', d, 'site-packages', 'cmk', 'shared_typing', '__init__.py')
      )
    status.sharedTypingPy.ok = sitePackages.some((p) => fs.existsSync(p))
  } catch {
    status.sharedTypingPy.ok = false
  }

  const frontendDist = path.join(wsPath, 'packages', 'cmk-frontend', 'dist')
  try {
    const stat = fs.lstatSync(frontendDist)
    if (stat.isSymbolicLink()) {
      const target = fs.readlinkSync(frontendDist)
      status.cmkFrontend.ok = fs.existsSync(target)
    } else {
      status.cmkFrontend.ok =
        fs.existsSync(path.join(frontendDist, 'index.html')) ||
        fs.readdirSync(frontendDist).length > 0
    }
  } catch {
    status.cmkFrontend.ok = false
  }

  status.mypyConfig.ok = fs.existsSync(path.join(wsPath, '.vscode', '.mypy.ini'))
  status.prettierConfig.ok = fs.existsSync(path.join(wsPath, '.vscode', '.prettier.config.cjs'))

  return status
}

export function getStaleTargets(status: BuildStatus): BuildTarget[] {
  return Object.values(status).filter((s) => !s.ok)
}

async function buildAllStale(status: BuildStatus): Promise<void> {
  const stale = getStaleTargets(status)
  if (stale.length === 0) {
    vscode.window.showInformationMessage('CMK: All build targets are up to date.')
    return
  }
  const seen = new Set<string>()
  for (const s of stale) {
    if (seen.has(s.commandId)) continue
    seen.add(s.commandId)
    await vscode.commands.executeCommand(s.commandId)
  }
}

interface QuickPickCommandItem extends vscode.QuickPickItem {
  commandId?: string
}

export function createStatusBar(
  context: vscode.ExtensionContext,
  commands: Record<string, CommandEntry>,
  onBuildComplete?: () => void
): { refreshStatus: (precomputed?: BuildStatus) => void } {
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50)
  statusBarItem.command = 'cmk.statusBarMenu'
  statusBarItem.show()
  context.subscriptions.push(statusBarItem)

  let currentStatus: BuildStatus = {}

  function refreshStatus(precomputed?: BuildStatus): void {
    if (precomputed) {
      currentStatus = precomputed
    } else {
      const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
      if (!wsPath) return
      currentStatus = checkBuildStatus(wsPath)
    }
    const stale = getStaleTargets(currentStatus)

    const pythonIssues = !currentStatus.venv?.ok || !currentStatus.sharedTypingPy?.ok
    const frontendIssues = !currentStatus.sharedTypingTs?.ok || !currentStatus.cmkFrontend?.ok
    profileManager.setIssues('python', pythonIssues)
    profileManager.setIssues('frontend', frontendIssues)

    if (stale.length === 0) {
      statusBarItem.text = '$(check) CMK'
      statusBarItem.tooltip = 'Checkmk: All builds up to date'
      statusBarItem.backgroundColor = undefined
    } else {
      statusBarItem.text = `$(warning) CMK (${stale.length})`
      statusBarItem.tooltip = `Checkmk: ${stale.length} target(s) need building\n${stale.map((s) => '  • ' + s.label).join('\n')}`
      statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground')
    }
  }

  refreshStatus()

  context.subscriptions.push(
    vscode.tasks.onDidEndTaskProcess((e) => {
      if (e.execution.task.source === 'CMK') {
        setTimeout(refreshStatus, 1000)
      }
    })
  )

  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (wsPath) {
    const watchers = [
      { pattern: 'packages/cmk-shared-typing/source/**', events: ['change', 'create', 'delete'] },
      { pattern: 'packages/cmk-frontend/src/**', events: ['change', 'create', 'delete'] },
      { pattern: '**/requirements*.txt', events: ['change'] },
      { pattern: '.git/HEAD', events: ['change'], delay: 500, branchSwitch: true }
    ]

    let _lastBranch = ''
    try {
      _lastBranch = execSync('git rev-parse --abbrev-ref HEAD', {
        cwd: wsPath,
        encoding: 'utf-8'
      }).trim()
    } catch {
      /* ignore */
    }

    for (const { pattern, events, delay, branchSwitch } of watchers) {
      const watcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(wsPath, pattern)
      )
      const handler = delay
        ? () =>
            setTimeout(() => {
              refreshStatus()
              if (branchSwitch) notifyBranchSwitch()
            }, delay)
        : () => refreshStatus()
      if (events.includes('change')) watcher.onDidChange(handler)
      if (events.includes('create')) watcher.onDidCreate(handler)
      if (events.includes('delete')) watcher.onDidDelete(handler)
      context.subscriptions.push(watcher)
    }

    function notifyBranchSwitch(): void {
      let newBranch: string
      try {
        newBranch = execSync('git rev-parse --abbrev-ref HEAD', {
          cwd: wsPath,
          encoding: 'utf-8'
        }).trim()
      } catch {
        return
      }
      if (newBranch === _lastBranch) return
      _lastBranch = newBranch

      const stale = getStaleTargets(currentStatus)
      if (stale.length === 0) return

      vscode.window
        .showWarningMessage(
          `CMK: Switched to ${newBranch} — ${stale.length} target(s) need building: ${stale.map((s) => s.label).join(', ')}`,
          'Build All Stale'
        )
        .then((choice) => {
          if (choice === 'Build All Stale') {
            buildAllStale(currentStatus)
          }
        })
    }
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.statusBarMenu', async () => {
      const stale = getStaleTargets(currentStatus)
      const items: QuickPickCommandItem[] = []

      if (stale.length > 0) {
        items.push({ label: 'Stale Targets', kind: vscode.QuickPickItemKind.Separator })
        items.push({
          label: '$(run-all) Build All Stale',
          description: `${stale.length} target(s)`,
          commandId: 'cmk.buildAllStale'
        })
        for (const s of stale) {
          items.push({
            label: `$(warning) ${s.label}`,
            description: 'needs building',
            commandId: s.commandId
          })
        }
        items.push({ label: '', kind: vscode.QuickPickItemKind.Separator })
      }

      items.push({ label: 'Commands', kind: vscode.QuickPickItemKind.Separator })
      for (const [id, entry] of Object.entries(commands)) {
        if (entry.requires && !profileManager.isActive(entry.requires)) continue
        const isStale = stale.some((s) => s.commandId === id)
        items.push({
          label: `$(terminal) ${entry.name}`,
          description: isStale
            ? '$(warning) stale'
            : entry.requires
              ? `[${entry.requires === 'frontend' ? 'UI' : entry.requires}]`
              : '',
          commandId: id
        })
      }

      const configCommands: { id: string; name: string }[] = [
        { id: 'cmk.regenerateMypyConfig', name: 'Regenerate mypy config' },
        { id: 'cmk.regeneratePrettierConfig', name: 'Regenerate prettier config' }
      ]
      for (const cmd of configCommands) {
        const isStale = stale.some((s) => s.commandId === cmd.id)
        items.push({
          label: `$(sync) ${cmd.name}`,
          description: isStale ? '$(warning) stale' : '',
          commandId: cmd.id
        })
      }

      items.push({ label: '', kind: vscode.QuickPickItemKind.Separator })
      items.push({
        label: '$(cloud-upload) Push to Gerrit',
        description: 'git push for review',
        commandId: 'cmk.pushToGerrit'
      })

      const picked = await vscode.window.showQuickPick(
        items.filter((i) => i.commandId || i.kind),
        {
          title:
            stale.length > 0
              ? `CMK ▸ ${stale.length} target(s) need building`
              : 'CMK ▸ Build Commands',
          placeHolder: 'Select a command to run'
        }
      )

      if (picked?.commandId) {
        vscode.commands.executeCommand(picked.commandId)
      }
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.buildAllStale', async () => {
      await buildAllStale(currentStatus)
      if (onBuildComplete) {
        onBuildComplete()
      } else {
        refreshStatus()
      }
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.refreshBuildStatus', refreshStatus)
  )

  const stale = getStaleTargets(currentStatus)
  if (stale.length > 0) {
    vscode.window
      .showWarningMessage(
        `CMK: ${stale.length} build target(s) need updating: ${stale.map((s) => s.label).join(', ')}`,
        'Build now'
      )
      .then((choice) => {
        if (choice === 'Build now') {
          vscode.commands.executeCommand('cmk.statusBarMenu')
        }
      })
  }

  return { refreshStatus }
}
