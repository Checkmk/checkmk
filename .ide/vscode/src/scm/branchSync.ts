/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log } from '../core/log'
import { safeExec } from '../core/shell'

const CONTEXT_KEY = 'cmk.branchSyncState'
const REF_SEP = '<<CMK>>'

type SyncState = 'unknown' | 'noupstream' | 'synced' | 'ahead' | 'behind' | 'diverged'

function repoRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

function computeSyncState(cwd: string): SyncState {
  const branch = safeExec('git symbolic-ref --short HEAD', { cwd })
  if (!branch) return 'unknown'
  const fmt = `'--format=%(upstream:short)${REF_SEP}%(upstream:track)'`
  const line = safeExec(`git for-each-ref ${fmt} refs/heads/${branch}`, { cwd })
  if (!line) return 'unknown'
  const [upstream, track] = line.split(REF_SEP)
  if (!upstream) return 'noupstream'
  const ahead = /ahead (\d+)/.exec(track ?? '')
  const behind = /behind (\d+)/.exec(track ?? '')
  if (ahead && behind) return 'diverged'
  if (ahead) return 'ahead'
  if (behind) return 'behind'
  return 'synced'
}

async function syncBranch(): Promise<void> {
  try {
    await vscode.commands.executeCommand('git.sync')
  } catch (err) {
    log(`git.sync failed: ${(err as Error).message}`)
  }
}

async function publishBranch(): Promise<void> {
  try {
    await vscode.commands.executeCommand('git.publish')
  } catch (err) {
    log(`git.publish failed: ${(err as Error).message}`)
  }
}

export function registerBranchSync(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.branchSync.synced', syncBranch),
    vscode.commands.registerCommand('cmk.branchSync.diverged', syncBranch),
    vscode.commands.registerCommand('cmk.branchSync.noupstream', publishBranch)
  )

  const refresh = (): void => {
    const cwd = repoRoot()
    const state: SyncState = cwd ? computeSyncState(cwd) : 'unknown'
    void vscode.commands.executeCommand('setContext', CONTEXT_KEY, state)
  }

  refresh()

  const wireGitApi = async (): Promise<void> => {
    try {
      const ext = vscode.extensions.getExtension('vscode.git')
      if (!ext) return
      if (!ext.isActive) await ext.activate()
      const api = ext.exports.getAPI(1)
      const wireRepo = (repo: { state: { onDidChange: vscode.Event<void> } }): void => {
        context.subscriptions.push(repo.state.onDidChange(refresh))
      }
      for (const repo of api.repositories) wireRepo(repo)
      context.subscriptions.push(api.onDidOpenRepository(wireRepo))
    } catch (err) {
      log(`Branch sync: git API wiring failed: ${(err as Error).message}`)
    }
  }
  void wireGitApi()

  const interval = setInterval(refresh, 60_000)
  context.subscriptions.push({ dispose: () => clearInterval(interval) })
}
