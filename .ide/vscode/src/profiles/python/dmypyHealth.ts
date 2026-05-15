/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { error, log, notifyInfo } from '../../core/log'
import { killAllDmypyDaemons } from './mypyConfig'

export interface DmypyHealthSnapshot {
  running: boolean
  stale: boolean
  configMtimeMs: number | null
  daemonStartMs: number | null
}

const EMPTY: DmypyHealthSnapshot = {
  running: false,
  stale: false,
  configMtimeMs: null,
  daemonStartMs: null
}

function isProcessAlive(pid: number): boolean {
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

/**
 * Detect whether a running dmypy daemon's view of the config is stale —
 * `.vscode/.mypy.ini` has been edited since the daemon started, so type
 * results no longer reflect the on-disk config until the user restarts it.
 *
 * Heuristic: compare the ini mtime against the `.dmypy.json` mtime (which
 * dmypy rewrites on start/stop). Synchronous fs.stat — microseconds; no
 * subprocesses on the sidebar refresh path.
 */
export function getDmypyHealthSnapshot(): DmypyHealthSnapshot {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return EMPTY

  const statusFile = path.join(wsPath, '.dmypy.json')
  const iniFile = path.join(wsPath, '.vscode', '.mypy.ini')

  let statusMtime: number
  let pid: number | null
  try {
    statusMtime = fs.statSync(statusFile).mtimeMs
    const status = JSON.parse(fs.readFileSync(statusFile, 'utf8')) as { pid?: number }
    pid = typeof status.pid === 'number' ? status.pid : null
  } catch {
    return EMPTY
  }

  const running = pid !== null && isProcessAlive(pid)
  if (!running) return { ...EMPTY, configMtimeMs: safeMtime(iniFile) }

  const configMtimeMs = safeMtime(iniFile)
  if (configMtimeMs === null) {
    return { running, stale: false, configMtimeMs, daemonStartMs: statusMtime }
  }
  // Allow a small skew (2s) to absorb concurrent writes during apply.
  const stale = configMtimeMs > statusMtime + 2000
  return { running, stale, configMtimeMs, daemonStartMs: statusMtime }
}

function safeMtime(p: string): number | null {
  try {
    return fs.statSync(p).mtimeMs
  } catch {
    return null
  }
}

export function registerDmypyHealth(): vscode.Disposable[] {
  return [
    vscode.commands.registerCommand('cmk.mypy.restartDmypy', async () => {
      try {
        await killAllDmypyDaemons()
        log('dmypy: restart requested via cockpit')
        await notifyInfo('CMK ▸ Mypy: dmypy daemon stopped — it will respawn on the next check.')
        vscode.commands.executeCommand('cmk.dashboard.refresh.overview')
      } catch (err) {
        error(`dmypy restart failed: ${(err as Error).message}`)
      }
    })
  ]
}
