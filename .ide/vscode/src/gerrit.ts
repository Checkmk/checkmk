/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { execSync } from 'child_process'
import * as vscode from 'vscode'

import { log, notifyError, notifyInfo, notifyWarn } from './core/log'

function getWorkspacePath(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

function git(args: string, cwd: string): string {
  return execSync(`git ${args}`, { cwd, encoding: 'utf-8' }).trim()
}

function getCurrentBranch(cwd: string): string {
  return git('rev-parse --abbrev-ref HEAD', cwd)
}

function getUnpushedCommitCount(cwd: string, remoteBranch: string): number {
  try {
    return parseInt(git(`rev-list --count ${remoteBranch}..HEAD`, cwd), 10)
  } catch {
    return parseInt(git('rev-list --count HEAD', cwd), 10)
  }
}

function hasUncommittedChanges(cwd: string): boolean {
  const status = git('status --porcelain', cwd)
  return status.length > 0
}

function createGerritStatusBar(context: vscode.ExtensionContext): void {
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 1000)
  item.command = 'cmk.pushToGerrit'
  item.text = '$(cloud-upload) Gerrit'
  item.tooltip = 'Push to Gerrit for review'
  item.show()
  context.subscriptions.push(item)
}

export function registerGerritPush(context: vscode.ExtensionContext): void {
  createGerritStatusBar(context)

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.pushToGerrit', async () => {
      log('Push to Gerrit')
      const cwd = getWorkspacePath()
      if (!cwd) {
        notifyError('CMK: No workspace folder found.')
        return
      }

      let branch: string
      try {
        branch = getCurrentBranch(cwd)
      } catch {
        notifyError('CMK: Not a git repository or git is not available.')
        return
      }

      if (branch === 'master' || branch === 'main') {
        notifyWarn('CMK: Refusing to push directly to master/main.')
        return
      }

      if (hasUncommittedChanges(cwd)) {
        const proceed = await vscode.window.showWarningMessage(
          'CMK: You have uncommitted changes. Push anyway?',
          'Push',
          'Cancel'
        )
        if (proceed !== 'Push') return
      }

      const targetBranch = await vscode.window.showInputBox({
        title: 'CMK ▸ Push to Gerrit',
        prompt: 'Target branch for review',
        value: 'master',
        placeHolder: 'master'
      })

      if (!targetBranch) return

      const refSpec = `HEAD:refs/for/${targetBranch}`

      let commitCount: number | string
      let commitLog = ''
      try {
        commitCount = getUnpushedCommitCount(cwd, `origin/${targetBranch}`)
        commitLog = git(`log --oneline origin/${targetBranch}..HEAD`, cwd)
      } catch {
        try {
          commitCount = getUnpushedCommitCount(cwd, `origin/${targetBranch}`)
        } catch {
          commitCount = '?'
        }
      }

      const commitLines = commitLog
        ? commitLog
            .split('\n')
            .map((l) => `  • ${l}`)
            .join('\n')
        : ''
      const detail = commitLines ? `Commits:\n${commitLines}` : ''

      const confirm = await vscode.window.showInformationMessage(
        `Push ${commitCount} commit(s) to Gerrit for review on ${targetBranch}?`,
        { modal: true, detail },
        'Push'
      )
      if (confirm !== 'Push') return

      const task = new vscode.Task(
        { type: 'cmk', task: 'gerrit-push' },
        vscode.TaskScope.Workspace,
        'Push to Gerrit',
        'CMK',
        new vscode.ShellExecution(`git push origin "${refSpec}"`, { cwd })
      )
      task.presentationOptions = { reveal: vscode.TaskRevealKind.Always }

      const execution = await vscode.tasks.executeTask(task)

      const disposable = vscode.tasks.onDidEndTaskProcess((e) => {
        if (e.execution === execution) {
          cleanup()
          if (e.exitCode === 0) {
            notifyInfo(
              'CMK: Pushed to Gerrit for review',
              `${branch} → ${targetBranch} (${commitCount} commit(s))`
            )
          } else {
            notifyError('CMK: Gerrit push failed', `exit code ${e.exitCode}`)
          }
        }
      })
      const fallback = vscode.tasks.onDidEndTask((e) => {
        if (e.execution === execution) {
          cleanup()
        }
      })
      function cleanup() {
        disposable.dispose()
        fallback.dispose()
      }
    })
  )
}
