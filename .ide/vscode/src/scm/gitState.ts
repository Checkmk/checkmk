/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { error, log, notifyError, notifyInfo } from '../core/log'
import { runCommand, waitForTask } from '../core/tasks'
import { gitAsync, repoRoot } from './git'
import { isPreCommitMissing, isPreCommitSkipping } from './preCommit'

export interface GitState {
  preCommitSkipping: boolean
  preCommitMissing: boolean
  qaTestDataDirty: boolean
  lastUpdated: number
}

const TTL_MS = 5_000
const QA_TEST_DATA_PATH = 'tests/qa-test-data'

let _state: GitState = {
  preCommitSkipping: false,
  preCommitMissing: false,
  qaTestDataDirty: false,
  lastUpdated: 0
}
let _inflight: Promise<void> | null = null
let _onRefresh: (() => void) | null = null

export function setGitStateRefreshCallback(cb: (() => void) | null): void {
  _onRefresh = cb
}

/**
 * Force the next `getGitState()` to re-probe, regardless of TTL. Used by
 * external watchers (e.g. the `.git/hooks/pre-commit*` watcher in sidebar.ts)
 * that already know the underlying state has changed and want the cockpit
 * to converge on the next refresh without waiting for the 5 s TTL.
 */
export function invalidateGitState(): void {
  _state = { ..._state, lastUpdated: 0 }
}

/**
 * Hard-reset `tests/qa-test-data` to the gitlink tracked by the parent repo,
 * discarding any local changes inside the submodule. Asks for confirmation
 * first because this is destructive.
 */
export function registerGitFixers(): vscode.Disposable[] {
  return [
    vscode.commands.registerCommand('cmk.cockpit.git.dismissPreCommit', async () => {
      const folder = vscode.workspace.workspaceFolders?.[0]
      const cfg = vscode.workspace.getConfiguration('cmk.cockpit.git', folder?.uri)
      const target = folder
        ? vscode.ConfigurationTarget.WorkspaceFolder
        : vscode.ConfigurationTarget.Workspace
      await cfg.update('ignorePreCommit', true, target)
      log('cockpit: pre-commit warning dismissed (cmk.cockpit.git.ignorePreCommit=true)')
    }),
    vscode.commands.registerCommand('cmk.cockpit.git.restorePreCommitWarning', async () => {
      const folder = vscode.workspace.workspaceFolders?.[0]
      const cfg = vscode.workspace.getConfiguration('cmk.cockpit.git', folder?.uri)
      const target = folder
        ? vscode.ConfigurationTarget.WorkspaceFolder
        : vscode.ConfigurationTarget.Workspace
      await cfg.update('ignorePreCommit', undefined, target)
      log('cockpit: pre-commit warning restored (cmk.cockpit.git.ignorePreCommit cleared)')
    }),
    vscode.commands.registerCommand('cmk.installPreCommit', async () => {
      const repo = repoRoot()
      if (!repo) {
        await notifyError('CMK: No workspace folder found.')
        return
      }
      log('git: installing pre-commit hook (cockpit info action)')
      const exec = runCommand('Install pre-commit hook', 'pre-commit install')
      if (!exec) {
        await notifyError('CMK: Could not start `pre-commit install`.')
        return
      }
      const rc = await waitForTask(exec)
      _state = { ..._state, lastUpdated: 0 }
      _onRefresh?.()
      if (rc === 0) await notifyInfo('CMK: pre-commit hook installed.')
      else await notifyError(`CMK: pre-commit install exited with code ${rc ?? '?'}.`)
    }),
    vscode.commands.registerCommand('cmk.fixQaTestDataSubmodule', async () => {
      const repo = repoRoot()
      if (!repo) {
        await notifyError('CMK: No workspace folder found.')
        return
      }
      const choice = await vscode.window.showWarningMessage(
        'Reset tests/qa-test-data to the tracked gitlink? Any uncommitted changes inside the submodule will be lost.',
        { modal: true },
        'Reset'
      )
      if (choice !== 'Reset') return
      log('git: hard-resetting tests/qa-test-data to tracked gitlink')
      // Read the tracked gitlink SHA from the parent's index and check out the
      // submodule worktree at exactly that SHA. Avoids `git submodule update
      // --init --force` because that falls back to the relative `../qa-test-
      // data` URL declared in .gitmodules, which git 2.38+ refuses over the
      // `file://` transport — so the action would fail with "fatal: transport
      // 'file' not allowed" even when the submodule is already correct.
      //
      // If the tracked SHA is missing locally we fetch it *by SHA*: a plain
      // `git fetch origin` only retrieves branch tips, so a gitlink that points
      // at a commit not reachable from any branch head stays absent and the
      // checkout fails with "fatal: reference is not a tree" (CMK-35371). When
      // the server rejects a want-by-sha request we fall back to a full
      // branches+tags fetch, which still lands the commit if it is reachable
      // from a ref. Statements are newline-joined under `set -e` rather than
      // chained with `&&` so the fetch/checkout flow isn't at the mercy of
      // `&&`/`||` precedence.
      const inner = [
        'set -e',
        "TRACKED_SHA=$(git ls-tree HEAD tests/qa-test-data | awk '{print $3}')",
        'test -n "$TRACKED_SHA" || { echo "qa-test-data not tracked in HEAD"; exit 1; }',
        'git -C tests/qa-test-data reset --hard',
        'git -C tests/qa-test-data clean -fdx',
        'if ! git -C tests/qa-test-data cat-file -e "${TRACKED_SHA}^{commit}" 2>/dev/null; then',
        '  git -C tests/qa-test-data fetch origin "$TRACKED_SHA" || git -C tests/qa-test-data fetch origin --tags',
        'fi',
        'git -C tests/qa-test-data checkout --force --detach "$TRACKED_SHA"'
      ].join('\n')
      const exec = runCommand('Reset tests/qa-test-data', inner)
      if (!exec) {
        await notifyError('CMK: Could not start the reset task.')
        return
      }
      const rc = await waitForTask(exec)
      // Invalidate the cached git state so the cockpit refreshes immediately.
      _state = { ..._state, lastUpdated: 0 }
      _onRefresh?.()
      if (rc === 0) await notifyInfo('CMK: tests/qa-test-data reset to tracked gitlink.')
      else await notifyError(`CMK: Reset task exited with code ${rc ?? '?'}.`)
    })
  ]
}

/** Sync getter for hot paths. Returns the cached value; kicks off a background
 *  refresh when stale and notifies via _onRefresh when the refresh completes. */
export function getGitState(): GitState {
  if (Date.now() - _state.lastUpdated > TTL_MS && !_inflight) {
    _inflight = (async () => {
      try {
        const repo = repoRoot()
        if (!repo) return
        const preCommitSkipping = isPreCommitSkipping(repo)
        const preCommitMissing = isPreCommitMissing(repo)
        // Submodule is dirty when the index entry's gitlink differs from the
        // submodule HEAD, OR when there are uncommitted changes inside it.
        // `git status --porcelain --ignore-submodules=none` prints either case.
        const status = await gitAsync(repo, [
          'status',
          '--porcelain=v1',
          '--ignore-submodules=none',
          '--',
          QA_TEST_DATA_PATH
        ])
        const qaTestDataDirty = status !== null && status.trim().length > 0
        _state = {
          preCommitSkipping,
          preCommitMissing,
          qaTestDataDirty,
          lastUpdated: Date.now()
        }
        _onRefresh?.()
      } catch (err) {
        error(`gitState refresh failed: ${(err as Error).message}`)
      } finally {
        _inflight = null
      }
    })()
  }
  return _state
}
