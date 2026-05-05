/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { log, notifyError, notifyWarn } from './core/log'

const CONTEXT_KEY = 'cmk.skipPreCommitEnabled'

function repoRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

function hookPaths(repo: string): { active: string; disabled: string } {
  return {
    active: path.join(repo, '.git', 'hooks', 'pre-commit'),
    disabled: path.join(repo, '.git', 'hooks', 'pre-commit.cmk-disabled')
  }
}

function isEnabled(repo: string): boolean {
  const { active, disabled } = hookPaths(repo)
  return !fs.existsSync(active) && fs.existsSync(disabled)
}

export function registerScm(context: vscode.ExtensionContext): void {
  const statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 1001)
  statusItem.command = 'cmk.toggleSkipPreCommit'
  context.subscriptions.push(statusItem)

  const sync = (): void => {
    const repo = repoRoot()
    if (!repo) {
      statusItem.hide()
      return
    }
    const skipping = isEnabled(repo)
    void vscode.commands.executeCommand('setContext', CONTEXT_KEY, skipping)
    if (skipping) {
      statusItem.text = '$(warning) pre-commit OFF'
      statusItem.tooltip = 'CMK: pre-commit hook is disabled. Click to re-enable.'
      statusItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground')
    } else {
      statusItem.text = '$(verified-filled)'
      statusItem.tooltip = 'CMK: pre-commit hook is active. Click to skip it.'
      statusItem.backgroundColor = undefined
    }
    statusItem.show()
  }

  const toggle = (): void => {
    const repo = repoRoot()
    if (!repo) {
      notifyWarn('CMK: No workspace folder found.')
      return
    }
    const { active, disabled } = hookPaths(repo)
    try {
      if (isEnabled(repo)) {
        fs.renameSync(disabled, active)
        log('pre-commit hook re-enabled')
      } else if (fs.existsSync(active)) {
        fs.renameSync(active, disabled)
        log('pre-commit hook disabled')
      } else {
        notifyWarn(
          'CMK: No .git/hooks/pre-commit found — nothing to disable. ' +
            'Run `pre-commit install` if you want hooks set up.'
        )
      }
    } catch (err) {
      notifyError(
        `CMK: Failed to toggle pre-commit: ${err instanceof Error ? err.message : String(err)}`
      )
    }
    sync()
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.toggleSkipPreCommit', toggle),
    vscode.commands.registerCommand('cmk.toggleSkipPreCommit.skipped', toggle)
  )

  const watcher = vscode.workspace.createFileSystemWatcher('**/.git/hooks/pre-commit*')
  watcher.onDidCreate(sync)
  watcher.onDidDelete(sync)
  watcher.onDidChange(sync)
  context.subscriptions.push(watcher)

  sync()
}
