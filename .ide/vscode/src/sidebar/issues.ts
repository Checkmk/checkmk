/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import * as profileManager from '../profiles/profileManager'
import type { StateCache } from './types'

const FAMILY_DISPLAY: Record<string, string> = {
  python: 'Python',
  frontend: 'UI',
  rust: 'Rust',
  bazel: 'Bazel',
  general: 'General',
  markdown: 'Markdown',
  cspell: 'Spelling'
}

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
    versionMismatch
  } = stateCache
  const items: IssueItem[] = []
  const warnColor = new vscode.ThemeColor('charts.yellow')
  const errorColor = new vscode.ThemeColor('charts.red')

  if (versionMismatch) {
    items.push({
      label: 'CMK Extension',
      description: `v${versionMismatch.installed} → v${versionMismatch.workspace}`,
      tooltip: `Installed v${versionMismatch.installed} ≠ workspace v${versionMismatch.workspace}. Click to rebuild & install.`,
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

  issuesProvider.refresh(items)

  issuesView.badge =
    items.length > 0
      ? {
          value: items.length,
          tooltip: `${items.length} issue${items.length > 1 ? 's' : ''} need attention`
        }
      : undefined
}
