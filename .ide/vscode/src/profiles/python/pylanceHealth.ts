/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as vscode from 'vscode'

import { error, log, notifyWarn } from '../../core/log'
import { safeExecAsync } from '../../core/shell'

const POLL_MS = 60_000
const WARN_SETTING = 'cmk.python.pylanceMemoryWarnMiB'
const WARN_DEFAULT = 2048

export interface PylanceHealthSnapshot {
  pid: number | null
  rssMiB: number | null
  thresholdMiB: number
  overThreshold: boolean
  extensionActive: boolean
  /** True while we are actively polling Pylance health (Linux + Python
   *  profile active). The sidebar shows the Pylance row whenever this is
   *  true; pid===null is rendered as "starting…". */
  monitored: boolean
}

let latest: PylanceHealthSnapshot = {
  pid: null,
  rssMiB: null,
  thresholdMiB: WARN_DEFAULT,
  overThreshold: false,
  extensionActive: false,
  monitored: false
}
let notifiedThisSession = false

export function getPylanceHealthSnapshot(): PylanceHealthSnapshot {
  return latest
}

function thresholdMiB(): number {
  return vscode.workspace.getConfiguration().get<number>(WARN_SETTING, WARN_DEFAULT) ?? WARN_DEFAULT
}

async function findPylancePid(): Promise<number | null> {
  const out = await safeExecAsync("pgrep -f 'vscode-pylance-[0-9].*server.bundle.js'")
  if (!out) return null
  const pid = parseInt(out.split('\n')[0].trim(), 10)
  return Number.isFinite(pid) ? pid : null
}

function readRssMiB(pid: number): number | null {
  try {
    const status = fs.readFileSync(`/proc/${pid}/status`, 'utf8')
    const match = status.match(/VmRSS:\s+(\d+)\s+kB/)
    if (!match) return null
    return Math.round(parseInt(match[1], 10) / 1024)
  } catch {
    return null
  }
}

async function maybeNotify(snap: PylanceHealthSnapshot): Promise<void> {
  if (!snap.overThreshold || notifiedThisSession) return
  notifiedThisSession = true
  const choice = await notifyWarn(
    `CMK ▸ Pylance memory high: ${snap.rssMiB} MiB (threshold ${snap.thresholdMiB} MiB).`,
    'Pylance RSS has crossed the configured threshold. Restarting the language server usually reclaims it; you can also raise cmk.python.pylanceMemoryWarnMiB if the threshold is too tight.',
    'Restart Pylance',
    'Dismiss'
  )
  if (choice === 'Restart Pylance') {
    await vscode.commands.executeCommand('python.analysis.restartLanguageServer')
    notifiedThisSession = false
  }
}

async function poll(onRefresh?: () => void): Promise<void> {
  const pid = await findPylancePid()
  const rss = pid !== null ? readRssMiB(pid) : null
  const threshold = thresholdMiB()
  const over = rss !== null && rss > threshold
  const extensionActive =
    vscode.extensions.getExtension('ms-python.vscode-pylance')?.isActive ?? false
  const next: PylanceHealthSnapshot = {
    pid,
    rssMiB: rss,
    thresholdMiB: threshold,
    overThreshold: over,
    extensionActive,
    monitored: true
  }
  const visibilityChanged =
    next.extensionActive !== latest.extensionActive ||
    (next.pid !== null) !== (latest.pid !== null) ||
    next.overThreshold !== latest.overThreshold
  latest = next
  if (rss !== null && pid !== null) {
    log(`Pylance (pid ${pid}) RSS = ${rss} MiB (threshold ${threshold})`)
  }
  if (visibilityChanged && onRefresh) onRefresh()
  await maybeNotify(latest)
}

/** Register the Pylance memory watcher. Linux only — uses /proc. No-op on
 *  other platforms, so the snapshot reports pid=null and consumers show no
 *  row. Polls at t=0 and t=15s to catch Pylance coming up shortly after
 *  activation, then every 60s; invokes a single per-session warn
 *  notification when RSS crosses `cmk.python.pylanceMemoryWarnMiB`
 *  (default 2048 MiB). */
export function registerPylanceHealth(onRefresh?: () => void): vscode.Disposable[] {
  if (process.platform !== 'linux') return []
  latest = { ...latest, monitored: true }
  onRefresh?.()
  const tick = (): void => {
    poll(onRefresh).catch((err) => error(`pylanceHealth poll failed: ${(err as Error).message}`))
  }
  tick()
  const earlyPoll = setTimeout(tick, 15_000)
  const interval = setInterval(tick, POLL_MS)
  return [
    {
      dispose: () => {
        clearTimeout(earlyPoll)
        clearInterval(interval)
        latest = { ...latest, monitored: false, pid: null, rssMiB: null }
        onRefresh?.()
      }
    }
  ]
}
