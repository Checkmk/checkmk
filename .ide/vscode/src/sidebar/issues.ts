/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { FAMILY_DISPLAY } from '../core/constants'
import * as profileManager from '../profiles/profileManager'
import type { StateCache } from './types'

const DISPLAY_TO_FAMILY = Object.fromEntries(Object.entries(FAMILY_DISPLAY).map(([k, v]) => [v, k]))

const ALWAYS_ON_FAMILIES = new Set(['bazel', 'general'])

export interface IssueItem {
  label: string
  description: string
  tooltip: string
  icon: string
  iconColor: vscode.ThemeColor
  command?: string
  commandArgs?: unknown[]
}

export class IssuesProvider implements vscode.TreeDataProvider<IssueItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<void>()
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event
  private _items: IssueItem[] = []

  refresh(items: IssueItem[]): void {
    this._items = items
    this._onDidChangeTreeData.fire()
  }

  getChildren(): IssueItem[] {
    return this._items
  }

  getTreeItem(item: IssueItem): vscode.TreeItem {
    const ti = new vscode.TreeItem(item.label, vscode.TreeItemCollapsibleState.None)
    ti.description = item.description || ''
    ti.tooltip = item.tooltip || item.label
    ti.iconPath = new vscode.ThemeIcon(item.icon, item.iconColor)
    if (item.command) {
      ti.command = { title: '', command: item.command, arguments: item.commandArgs || [] }
    }
    return ti
  }
}

export function updateIssues(
  issuesView: vscode.TreeView<IssueItem> | null,
  issuesProvider: IssuesProvider | null,
  stateCache: StateCache
): void {
  if (!issuesView || !issuesProvider) return

  const {
    buildStatus,
    settingsMismatches,
    extensionHealth,
    pythonEnvsActive,
    devSiteTools,
    versionMismatch,
    mypyTargets,
    allocator
  } = stateCache
  const items: IssueItem[] = []
  const warnColor = new vscode.ThemeColor('charts.yellow')
  const errorColor = new vscode.ThemeColor('charts.red')

  if (versionMismatch) {
    items.push({
      label: 'CMK Extension',
      description: `v${versionMismatch.installed} → v${versionMismatch.workspace}`,
      tooltip: `Installed v${versionMismatch.installed} ≠ workspace v${versionMismatch.workspace}. Click to install.`,
      icon: 'extensions',
      iconColor: warnColor,
      command: 'cmk.rebuildExtension'
    })
  }

  for (const [, s] of Object.entries(buildStatus)) {
    if (s.ok) continue
    items.push({
      label: s.label,
      description: 'needs building',
      tooltip: `Click to build ${s.label}`,
      icon: 'tools',
      iconColor: warnColor,
      command: s.commandId
    })
  }

  const seenKeys = new Set<string>()
  const activeMismatches = settingsMismatches.filter((m) => {
    if (seenKeys.has(m.key)) return false
    const family = DISPLAY_TO_FAMILY[m.family]
    if (!family) return false
    if (!ALWAYS_ON_FAMILIES.has(family) && !profileManager.isActive(family)) return false
    seenKeys.add(m.key)
    return true
  })
  for (const m of activeMismatches) {
    items.push({
      label: m.key,
      description: `${m.family} · ${m.scope}`,
      tooltip: `Click to apply: ${m.key} = ${JSON.stringify(m.expected)}`,
      icon: 'settings-gear',
      iconColor: warnColor,
      command: 'cmk.applySetting',
      commandArgs: [m.key, m.expected, m.scope]
    })
  }

  for (const f of extensionHealth) {
    if (!f.required) continue
    for (const e of f.extensions) {
      if (e.installed) continue
      items.push({
        label: e.id,
        description: 'not installed',
        tooltip: `Required extension ${e.id} is missing`,
        icon: 'extensions',
        iconColor: errorColor,
        command: 'workbench.extensions.search',
        commandArgs: [e.id]
      })
    }
  }

  if (pythonEnvsActive) {
    items.push({
      label: 'Python Environments',
      description: 'high resource usage',
      tooltip:
        'ms-python.vscode-python-envs continuously scans for interpreters. Click to open and disable.',
      icon: 'warning',
      iconColor: warnColor,
      command: 'extension.open',
      commandArgs: ['ms-python.vscode-python-envs']
    })
  }

  if (!stateCache.configInWorkspace) {
    items.push({
      label: 'No config recommendations',
      description: 'evaluate extensions & settings independently',
      tooltip:
        'No workspace configuration files found in .ide/vscode/config/. Please evaluate extensions and settings independently.',
      icon: 'warning',
      iconColor: warnColor
    })
  }

  if (devSiteTools && !devSiteTools.installed) {
    items.push({
      label: 'cmk-dev-site',
      description: 'not installed',
      tooltip: 'Click to install cmk-dev-site via pipx',
      icon: 'package',
      iconColor: warnColor,
      command: 'cmk.installDevSite'
    })
  }

  if (mypyTargets) {
    const stagedUnion = new Set<string>([
      ...mypyTargets.stagedActiveAdd,
      ...mypyTargets.stagedActiveRemove,
      ...mypyTargets.stagedBaselineAdd,
      ...mypyTargets.stagedBaselineRemove
    ])
    if (stagedUnion.size > 0) {
      items.push({
        label: 'Mypy: staged changes',
        description: `${stagedUnion.size} pending`,
        tooltip: `Staged: ${[...stagedUnion].sort().join(', ')}\nClick to apply (restarts dmypy).`,
        icon: 'diff-added',
        iconColor: warnColor,
        command: 'cmk.mypy.applyStagedTargets'
      })
    }
  }

  if (allocator && mypyTargets?.pythonProfileActive) {
    if (allocator.mode === 'jemalloc') {
      const reasons: string[] = []
      if (!allocator.libraryAvailable) reasons.push('libjemalloc not found')
      if (!allocator.wrapperExists) reasons.push('wrapper missing')
      if (!allocator.dmypyExecutableMatches) reasons.push('dmypyExecutable mismatch')
      if (!allocator.runUsingInterpreterOff) reasons.push('runUsingActiveInterpreter still true')
      if (reasons.length > 0) {
        items.push({
          label: 'Mypy: allocator',
          description: `jemalloc enabled but not active — ${reasons.join(', ')}`,
          tooltip:
            'jemalloc is configured but one or more settings are stale. Click to re-run the reconciliation.',
          icon: 'warning',
          iconColor: warnColor,
          command: 'cmk.mypy.reapplyJemalloc'
        })
      }
    } else if (!allocator.recommendationDismissed) {
      items.push(
        allocator.libraryAvailable
          ? {
              label: 'Mypy: allocator',
              description: 'jemalloc available',
              tooltip:
                'dmypy is running under the default allocator. Switching to jemalloc caps long-running RSS growth. Click to enable.',
              icon: 'warning',
              iconColor: warnColor,
              command: 'workbench.action.openSettings',
              commandArgs: ['cmk.mypy.allocator']
            }
          : {
              label: 'Mypy: allocator',
              description: 'libjemalloc not installed',
              tooltip:
                'dmypy is running under the default allocator. Install jemalloc to let the extension cap long-running RSS growth. Click to run the install command.',
              icon: 'warning',
              iconColor: warnColor,
              command: 'cmk.mypy.installJemalloc'
            }
      )
    }
  }

  issuesProvider.refresh(items)

  issuesView.badge =
    items.length > 0
      ? {
          value: items.length,
          tooltip: `${items.length} issue${items.length > 1 ? 's' : ''} need attention`
        }
      : undefined
}
