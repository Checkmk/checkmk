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

  const progressItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 1002)
  progressItem.command = 'git.showOutput'
  progressItem.text = '$(sync~spin) pre-commit running…'
  progressItem.tooltip = 'CMK: a git commit is in progress. Click to open the Git output channel.'
  context.subscriptions.push(progressItem)

  const QUIET_MS = 2000
  const POLL_MS = 250
  let pollTimer: NodeJS.Timeout | undefined
  let lastSeen = 0
  let outputShown = false

  const lockPath = (): string | undefined => {
    const repo = repoRoot()
    return repo ? path.join(repo, '.git', 'index.lock') : undefined
  }

  const beginActivity = (): void => {
    const lp = lockPath()
    if (!lp) return
    lastSeen = Date.now()
    progressItem.show()
    if (!outputShown) {
      const cfg = vscode.workspace.getConfiguration('cmk.scm')
      if (cfg.get<boolean>('autoShowGitOutputOnCommit', true)) {
        void vscode.commands.executeCommand('git.showOutput')
      }
      outputShown = true
    }
    if (pollTimer) return
    pollTimer = setInterval(() => {
      if (fs.existsSync(lp)) {
        lastSeen = Date.now()
        return
      }
      if (Date.now() - lastSeen >= QUIET_MS) {
        clearInterval(pollTimer!)
        pollTimer = undefined
        outputShown = false
        progressItem.hide()
      }
    }, POLL_MS)
  }

  const indexLockWatcher = vscode.workspace.createFileSystemWatcher('**/.git/index.lock')
  indexLockWatcher.onDidCreate(beginActivity)
  indexLockWatcher.onDidChange(beginActivity)
  context.subscriptions.push(indexLockWatcher, {
    dispose: () => {
      if (pollTimer) clearInterval(pollTimer)
    }
  })
}
