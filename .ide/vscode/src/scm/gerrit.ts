/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log, notifyError, notifyInfo, notifyWarn } from '../core/log'
import { gitAsync, repoRoot } from './git'

async function getCurrentBranch(cwd: string): Promise<string | null> {
  return gitAsync(cwd, ['rev-parse', '--abbrev-ref', 'HEAD'])
}

async function getUnpushedCommitCount(cwd: string, remoteBranch: string): Promise<number | null> {
  const ranged = await gitAsync(cwd, ['rev-list', '--count', `${remoteBranch}..HEAD`])
  if (ranged !== null) return parseInt(ranged, 10) || 0
  const all = await gitAsync(cwd, ['rev-list', '--count', 'HEAD'])
  return all !== null ? parseInt(all, 10) || 0 : null
}

async function hasUncommittedChanges(cwd: string): Promise<boolean> {
  const status = await gitAsync(cwd, ['status', '--porcelain'])
  return !!status && status.length > 0
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
      const cwd = repoRoot()
      if (!cwd) {
        notifyError('CMK: No workspace folder found.')
        return
      }

      // Kick off branch + dirty-tree checks in parallel — git status on a
      // large working tree alone can take ~250 ms, so don't serialise.
      const [branch, dirty] = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Window, title: 'CMK: Checking git state…' },
        () => Promise.all([getCurrentBranch(cwd), hasUncommittedChanges(cwd)])
      )

      if (branch === null) {
        notifyError('CMK: Not a git repository or git is not available.')
        return
      }

      if (branch === 'master' || branch === 'main') {
        notifyWarn('CMK: Refusing to push directly to master/main.')
        return
      }

      if (dirty) {
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

      const [countResult, logResult] = await Promise.all([
        getUnpushedCommitCount(cwd, `origin/${targetBranch}`),
        gitAsync(cwd, ['log', '--oneline', `origin/${targetBranch}..HEAD`])
      ])
      const commitCount: number | string = countResult ?? '?'
      const commitLog = logResult ?? ''

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
