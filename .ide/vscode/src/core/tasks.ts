/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { notifyError } from './log'

export function getExtendedPath(): string {
  const home = os.homedir()
  const candidatePaths = [
    '/home/linuxbrew/.linuxbrew/bin',
    '/home/linuxbrew/.linuxbrew/sbin',
    path.join(home, 'go', 'bin'),
    path.join(home, '.local', 'bin'),
    path.join(home, '.pyenv', 'bin'),
    path.join(home, '.pyenv', 'shims'),
    // NVM current version bin (resolved via default alias symlink)
    ...(() => {
      try {
        const defaultPath = path.join(home, '.nvm', 'alias', 'default')
        const ver = fs.readFileSync(defaultPath, 'utf-8').trim()
        const binPath = path.join(home, '.nvm', 'versions', 'node', `v${ver}`, 'bin')
        if (fs.existsSync(binPath)) return [binPath]
      } catch {
        /* ignore */
      }
      return []
    })(),
    '/usr/local/go/bin'
  ]
  const currentPath = process.env.PATH || ''
  const missing = candidatePaths.filter((p) => !currentPath.includes(p) && fs.existsSync(p))
  return missing.length > 0 ? `${missing.join(':')}:${currentPath}` : currentPath
}

export interface RunCommandOptions {
  // Force commands (e.g. the long-running UCL dev server) run in their own
  // reusable terminal and force-restart on re-run: any live instance is
  // terminated first so a fresh run always launches in place. Without this,
  // commands keep VS Code's default shared-panel behaviour.
  force?: boolean
}

export function runCommand(
  name: string,
  command: string,
  options: RunCommandOptions = {}
): vscode.TaskExecution | undefined {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!workspaceFolder) {
    notifyError('No workspace folder found')
    return
  }

  if (options.force) {
    // VS Code dedupes tasks by identity, so an already-active task would
    // otherwise be terminated without a fresh one launching. Explicitly
    // terminate any live instance first, so the executeTask() below always
    // starts a clean new run.
    for (const active of vscode.tasks.taskExecutions) {
      if (active.task.source === 'CMK' && active.task.name === name) {
        active.terminate()
      }
    }
  }

  const task = new vscode.Task(
    { type: 'cmk', task: name },
    vscode.TaskScope.Workspace,
    name,
    'CMK',
    new vscode.ShellExecution(command, {
      cwd: workspaceFolder,
      env: { PATH: getExtendedPath() }
    })
  )
  // Dedicated panel: the command reuses its own terminal across runs, so a
  // restart replaces the previous output in place instead of leaking terminals.
  task.presentationOptions = {
    reveal: vscode.TaskRevealKind.Always,
    ...(options.force ? { panel: vscode.TaskPanelKind.Dedicated } : {})
  }

  // vscode.tasks.executeTask returns a Thenable<TaskExecution>,
  // but callers treat the return as the execution itself.
  // We keep the same contract: return is used as a truthy check + passed to waitForTask.
  return vscode.tasks.executeTask(task) as unknown as vscode.TaskExecution
}

export function waitForTask(
  execution: vscode.TaskExecution,
  timeoutMs = 600000
): Promise<number | undefined> {
  return new Promise((resolve) => {
    const disposable = vscode.tasks.onDidEndTaskProcess((e) => {
      if (e.execution === execution) {
        cleanup()
        resolve(e.exitCode)
      }
    })
    const fallback = vscode.tasks.onDidEndTask((e) => {
      if (e.execution === execution) {
        cleanup()
        resolve(undefined)
      }
    })
    const timer = setTimeout(() => {
      cleanup()
      resolve(undefined)
    }, timeoutMs)
    function cleanup() {
      disposable.dispose()
      fallback.dispose()
      clearTimeout(timer)
    }
  })
}
