/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { type Issue, enumerateIssues, sortIssues, summaryHeader } from './overview/domainSummary'
import type { StateCache } from './types'

export interface IssueItem {
  id: string
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
    ti.id = item.id
    ti.description = item.description || ''
    ti.tooltip = item.tooltip || item.label
    ti.iconPath = new vscode.ThemeIcon(item.icon, item.iconColor)
    if (item.command) {
      ti.command = { title: '', command: item.command, arguments: item.commandArgs || [] }
    }
    return ti
  }
}

const SEVERITY_COLOR: Record<Issue['severity'], vscode.ThemeColor> = {
  info: new vscode.ThemeColor('charts.blue'),
  warning: new vscode.ThemeColor('charts.yellow'),
  critical: new vscode.ThemeColor('charts.red')
}

function toItem(issue: Issue): IssueItem {
  return {
    id: issue.id,
    label: issue.label,
    description: issue.description,
    tooltip: issue.tooltip,
    icon: issue.icon,
    iconColor: SEVERITY_COLOR[issue.severity],
    command: issue.command,
    commandArgs: issue.commandArgs
  }
}

export function updateIssues(
  issuesView: vscode.TreeView<IssueItem> | null,
  issuesProvider: IssuesProvider | null,
  stateCache: StateCache
): void {
  if (!issuesView || !issuesProvider) return

  const issues = sortIssues(enumerateIssues(stateCache))
  const items = issues.map(toItem)
  issuesProvider.refresh(items)

  issuesView.description = summaryHeader(issues)
  // Activity-bar badge counts only attention-worthy issues — info-level
  // entries are dismissed/informational and shouldn't bump the badge.
  const active = issues.filter((i) => i.severity !== 'info').length
  issuesView.badge =
    active > 0
      ? {
          value: active,
          tooltip: `${active} issue${active > 1 ? 's' : ''} need attention`
        }
      : undefined
}
