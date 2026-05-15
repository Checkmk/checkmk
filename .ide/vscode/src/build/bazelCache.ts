/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { error, log, notifyError, notifyInfo } from '../core/log'
import { safeExecAsync } from '../core/shell'
import { runCommand, waitForTask } from '../core/tasks'

export interface BazelCacheSnapshot {
  sizeBytes: number | null
  thresholdGiB: number
  cachePath: string | null
  overThreshold: boolean
}

const DEFAULT_THRESHOLD_GIB = 50
const TTL_MS = 5 * 60 * 1000

const EMPTY: BazelCacheSnapshot = {
  sizeBytes: null,
  thresholdGiB: DEFAULT_THRESHOLD_GIB,
  cachePath: null,
  overThreshold: false
}

let _snapshot: BazelCacheSnapshot = EMPTY
let _lastUpdated = 0
let _inflight: Promise<void> | null = null
let _onRefresh: (() => void) | null = null

export function setBazelCacheRefreshCallback(cb: (() => void) | null): void {
  _onRefresh = cb
}

function expandHome(p: string): string {
  if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2))
  if (p === '~') return os.homedir()
  return p
}

function resolveDiskCachePath(wsPath: string): string | null {
  // Walk .bazelrc looking for the most recent --disk_cache flag. Honours
  // both `build --disk_cache=` and `common:linux --disk_cache=` forms.
  const candidates = [path.join(wsPath, '.bazelrc'), path.join(os.homedir(), '.bazelrc')]
  let found: string | null = null
  for (const file of candidates) {
    try {
      const content = fs.readFileSync(file, 'utf8')
      for (const line of content.split('\n')) {
        const m = line.match(/--disk_cache=(\S+)/)
        if (m) found = expandHome(m[1].replace(/\/+$/, ''))
      }
    } catch {
      // Missing or unreadable .bazelrc — skip.
    }
  }
  if (!found) return null
  return found
}

function getConfiguredThresholdGiB(): number {
  const cfg = vscode.workspace.getConfiguration('cmk.bazel')
  const v = cfg.get<number>('cacheSizeWarnGiB', DEFAULT_THRESHOLD_GIB)
  return typeof v === 'number' && v > 0 ? v : DEFAULT_THRESHOLD_GIB
}

async function probeSize(cachePath: string): Promise<number | null> {
  // `du -sb` returns size in bytes. POSIX du doesn't support -b but GNU does;
  // this codebase already shells out to GNU du elsewhere.
  const out = await safeExecAsync(`du -sb ${shellQuote(cachePath)}`, { timeout: 30_000 })
  if (!out) return null
  const m = out.match(/^(\d+)/)
  return m ? parseInt(m[1], 10) : null
}

function shellQuote(s: string): string {
  return `'${s.replace(/'/g, "'\\''")}'`
}

/**
 * Stale-while-revalidate getter. Returns cached snapshot synchronously, kicks
 * off a background `du -sb` when stale. The first call returns EMPTY until
 * the probe completes and triggers `_onRefresh`.
 */
export function getBazelCacheSnapshot(): BazelCacheSnapshot {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return EMPTY

  const thresholdGiB = getConfiguredThresholdGiB()
  // Threshold can change without invalidating size — recompute overThreshold
  // every call so toggling the setting reflects immediately.
  const sized = _snapshot.sizeBytes !== null
  const overThreshold = sized && _snapshot.sizeBytes! > thresholdGiB * 1024 ** 3
  const view: BazelCacheSnapshot = { ..._snapshot, thresholdGiB, overThreshold }

  if (Date.now() - _lastUpdated > TTL_MS && !_inflight) {
    _inflight = (async () => {
      try {
        const cachePath = resolveDiskCachePath(wsPath)
        if (!cachePath || !fs.existsSync(cachePath)) {
          _snapshot = { ...EMPTY, thresholdGiB, cachePath }
          _lastUpdated = Date.now()
          _onRefresh?.()
          return
        }
        const sizeBytes = await probeSize(cachePath)
        _snapshot = {
          sizeBytes,
          thresholdGiB,
          cachePath,
          overThreshold: sizeBytes !== null && sizeBytes > thresholdGiB * 1024 ** 3
        }
        _lastUpdated = Date.now()
        _onRefresh?.()
      } catch (err) {
        error(`bazelCache probe failed: ${(err as Error).message}`)
      } finally {
        _inflight = null
      }
    })()
  }

  return view
}

export function registerBazelCache(): vscode.Disposable[] {
  return [
    vscode.commands.registerCommand('cmk.bazel.cleanDiskCache', async () => {
      const cachePath = _snapshot.cachePath
      if (!cachePath) {
        await notifyError('CMK ▸ Bazel: No disk_cache configured in .bazelrc.')
        return
      }
      const choice = await vscode.window.showWarningMessage(
        `Delete the entire Bazel disk cache at ${cachePath}? Subsequent builds will refill it from scratch.`,
        { modal: true },
        'Delete'
      )
      if (choice !== 'Delete') return
      log(`bazel: deleting disk cache at ${cachePath}`)
      const exec = runCommand('Bazel — clean disk cache', `rm -rf ${shellQuote(cachePath)}`)
      if (!exec) {
        await notifyError('CMK ▸ Bazel: Could not start the cleanup task.')
        return
      }
      const rc = await waitForTask(exec)
      _lastUpdated = 0
      _onRefresh?.()
      vscode.commands.executeCommand('cmk.dashboard.refresh.overview')
      if (rc === 0) await notifyInfo(`CMK ▸ Bazel: Disk cache cleared (${cachePath}).`)
      else await notifyError(`CMK ▸ Bazel: Cleanup task exited with code ${rc ?? '?'}.`)
    })
  ]
}
