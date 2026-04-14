/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { shellEscape } from '../core/config'
import { log } from '../core/log'
import { safeExec } from '../core/shell'
import { runCommand, waitForTask } from '../core/tasks'
import { ensureKeepaliveAuth, hasKeepalive, runInKeepaliveTerminal } from './sudoBridge'

const LOG_LIST_DIR = path.join(os.tmpdir(), 'cmk-omd-logs')

function sudoSh(inner: string): string {
  return `sudo sh -c "${inner.replace(/"/g, '\\"')}"`
}

export const LOG_SCHEME = 'cmk-omd-log'

export interface LogEntry {
  /** Stable identifier (matches log.io source name). */
  source: string
  /** OMD service that owns this log (matches `OmdService.name`). */
  service?: string
  /** Glob pattern with `$SITE` placeholder. Supports `*` and `**`. */
  path: string
}

export interface ResolvedLog {
  source: string
  service?: string
  /** Absolute file path. */
  file: string
}

/**
 * Hardcoded catalog of OMD log files. Mirrors `cmk-dev-serve/logio-file.json`
 * with explicit `service` mapping for sidebar service-row buttons.
 */
const LOG_CATALOG: LogEntry[] = [
  // cmc / core
  { source: 'cmc.log', service: 'cmc', path: '/omd/sites/$SITE/var/log/cmc.log' },
  { source: 'alerts.log', service: 'cmc', path: '/omd/sites/$SITE/var/log/alerts.log' },
  { source: 'notify.log', service: 'cmc', path: '/omd/sites/$SITE/var/log/notify.log' },
  // apache / GUI
  {
    source: 'apache-logs',
    service: 'apache',
    path: '/omd/sites/$SITE/var/log/apache/**/*_log'
  },
  { source: 'web.log', service: 'apache', path: '/omd/sites/$SITE/var/log/web.log' },
  { source: 'security.log', service: 'apache', path: '/omd/sites/$SITE/var/log/security.log' },
  // discrete services
  { source: 'mkeventd.log', service: 'mkeventd', path: '/omd/sites/$SITE/var/log/mkeventd.log' },
  {
    source: 'mkeventd-logs',
    service: 'mkeventd',
    path: '/omd/sites/$SITE/var/log/mkeventd/**/*.log'
  },
  {
    source: 'mknotifyd.log',
    service: 'mknotifyd',
    path: '/omd/sites/$SITE/var/log/mknotifyd.log'
  },
  {
    source: 'rrdcached.log',
    service: 'rrdcached',
    path: '/omd/sites/$SITE/var/log/rrdcached.log'
  },
  {
    source: 'redis-server.log',
    service: 'redis',
    path: '/omd/sites/$SITE/var/log/redis-server.log'
  },
  {
    source: 'stunnel-server.log',
    service: 'stunnel',
    path: '/omd/sites/$SITE/var/log/stunnel-server.log'
  },
  { source: 'liveproxyd', service: 'liveproxyd', path: '/omd/sites/$SITE/var/log/liveproxyd.*' },
  { source: 'dcd.log', service: 'dcd', path: '/omd/sites/$SITE/var/log/dcd.log' },
  {
    source: 'rabbitmq-logs',
    service: 'rabbitmq',
    path: '/omd/sites/$SITE/var/log/rabbitmq/**/*.log'
  },
  { source: 'jaeger.log', service: 'jaeger', path: '/omd/sites/$SITE/var/log/jaeger.log' },
  {
    source: 'agent-receiver-logs',
    service: 'agent-receiver',
    path: '/omd/sites/$SITE/var/log/agent-receiver/**/*.log'
  },
  {
    source: 'automation-helper-logs',
    service: 'automation-helper',
    path: '/omd/sites/$SITE/var/log/automation-helper/**/*.log'
  },
  {
    source: 'piggyback-hub.log',
    service: 'piggyback-hub',
    path: '/omd/sites/$SITE/var/log/piggyback-hub.log'
  },
  {
    source: 'ui-job-scheduler-logs',
    service: 'ui-job-scheduler',
    path: '/omd/sites/$SITE/var/log/ui-job-scheduler/**/*.log'
  },
  { source: 'xinetd.log', service: 'xinetd', path: '/omd/sites/$SITE/var/log/xinetd.log' },
  // site-level residue (no owning service)
  { source: 'diskspace.log', path: '/omd/sites/$SITE/var/log/diskspace.log' },
  { source: 'licensing.log', path: '/omd/sites/$SITE/var/log/licensing.log' },
  { source: 'telemetry.log', path: '/omd/sites/$SITE/var/log/telemetry.log' }
]

interface SiteLogListing {
  files: string[]
  /** True when neither direct nor sudo enumeration produced any output. */
  failed: boolean
}

/**
 * Enumerate every regular file under `/omd/sites/<site>/var/log/`.
 * Prefers the keepalive terminal's authenticated sudo session (no re-prompt).
 * Falls back to a fresh `runCommand` terminal task if the bridge is unavailable
 * or times out.
 */
async function listAllSiteLogFiles(site: string): Promise<SiteLogListing> {
  const baseDir = `/omd/sites/${site}/var/log`
  const findCmd = `find ${shellEscape(baseDir)} -type f -print 2>/dev/null`

  // Fast paths that don't need sudo or run via the caller's TTY
  const direct = safeExec(findCmd, { timeout: 5000 })
  if (direct) return { files: direct.split('\n').filter(Boolean), failed: false }
  const sudoN = safeExec(`sudo -n ${findCmd}`, { timeout: 5000 })
  if (sudoN) return { files: sudoN.split('\n').filter(Boolean), failed: false }

  // Prefer the keepalive bridge. If no session is active, auto-prompt auth.
  if (!hasKeepalive()) {
    const authed = await ensureKeepaliveAuth()
    if (!authed) return { files: [], failed: true }
  }
  const bridged = await runInKeepaliveTerminal(findCmd)
  if (bridged) {
    const files = bridged.output.split('\n').filter((l) => l.startsWith('/'))
    return { files, failed: bridged.exitCode !== 0 && files.length === 0 }
  }

  // Bridge unavailable / timed out → fall back to a dedicated task terminal.
  fs.mkdirSync(LOG_LIST_DIR, { recursive: true })
  const listFile = path.join(LOG_LIST_DIR, `${site}.list`)
  const inner =
    `find ${shellEscape(baseDir)} -type f -print > ${shellEscape(listFile)} 2>&1 ; ` +
    `chmod 644 ${shellEscape(listFile)}`
  const execMaybe = runCommand(`OMD ${site}: discover logs`, sudoSh(inner))
  if (!execMaybe) return { files: [], failed: true }
  const execution = await (execMaybe as unknown as Promise<vscode.TaskExecution>)
  await waitForTask(execution)
  try {
    const content = fs.readFileSync(listFile, 'utf-8')
    const files = content.split('\n').filter((l) => l.startsWith('/'))
    return { files, failed: files.length === 0 }
  } catch {
    return { files: [], failed: true }
  }
}

function applySite(pattern: string, site: string): string {
  return pattern.replace(/\$SITE/g, site)
}

// Convert a shell glob (supporting `*` and `**`) to a regex anchored on both
// ends. `**` matches any path. A `**/` segment matches zero-or-more directory
// levels, so `foo/**/bar` matches both `foo/bar` and `foo/a/b/bar`.
function globToRegex(glob: string): RegExp {
  let re = ''
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i]
    if (c === '*' && glob[i + 1] === '*') {
      if (glob[i + 2] === '/') {
        re += '(?:.*/)?'
        i += 2
      } else {
        re += '.*'
        i += 1
      }
    } else if (c === '*') {
      re += '[^/]*'
    } else if ('.+?^${}()|[]\\'.includes(c)) {
      re += '\\' + c
    } else {
      re += c
    }
  }
  return new RegExp('^' + re + '$')
}

/** All log files that exist for a site, in catalog order. */
export async function resolveLogsForSite(site: string): Promise<{
  logs: ResolvedLog[]
  failed: boolean
}> {
  const { files, failed } = await listAllSiteLogFiles(site)
  const out: ResolvedLog[] = []
  for (const entry of LOG_CATALOG) {
    const re = globToRegex(applySite(entry.path, site))
    for (const file of files) {
      if (re.test(file)) {
        out.push({ source: entry.source, service: entry.service, file })
      }
    }
  }
  return { logs: out, failed }
}

/** Logs that belong to a specific OMD service. */
export async function resolveLogsForService(
  site: string,
  service: string
): Promise<{ logs: ResolvedLog[]; failed: boolean }> {
  const { files, failed } = await listAllSiteLogFiles(site)
  const out: ResolvedLog[] = []
  for (const entry of LOG_CATALOG) {
    if (entry.service !== service) continue
    const re = globToRegex(applySite(entry.path, site))
    for (const file of files) {
      if (re.test(file)) {
        out.push({ source: entry.source, service: entry.service, file })
      }
    }
  }
  return { logs: out, failed }
}

/** Open the log via `sudo tail -F` in a new VS Code terminal so new lines
 *  stream live. Reusing the editor-document content provider would require
 *  re-spawning a sudo task on every refresh — the terminal handles auth
 *  once, then streams forever. */
async function openLog(site: string, log_: ResolvedLog): Promise<void> {
  const term = vscode.window.createTerminal({ name: `tail: ${site}/${log_.source}` })
  term.show()
  term.sendText(`sudo tail -F ${shellEscape(log_.file)}`)
}

/** Show a QuickPick of logs; resolves with the chosen log or undefined. */
async function pickLog(logs: ResolvedLog[], placeHolder: string): Promise<ResolvedLog | undefined> {
  if (logs.length === 0) return undefined
  if (logs.length === 1) return logs[0]
  const items = logs.map((l) => ({
    label: l.source,
    description: l.service ? `[${l.service}]` : '',
    detail: l.file,
    log: l
  }))
  const picked = await vscode.window.showQuickPick(items, {
    placeHolder,
    matchOnDescription: true,
    matchOnDetail: true
  })
  return picked?.log
}

/** Open the picker for all logs of a site. */
export async function showSiteLogs(site: string): Promise<void> {
  log(`OMD logs: site ${site}`)
  const { logs, failed } = await resolveLogsForSite(site)
  if (failed) {
    vscode.window.showErrorMessage(
      `Could not read /omd/sites/${site}/var/log. The sudo task was cancelled or failed.`
    )
    return
  }
  if (logs.length === 0) {
    vscode.window.showInformationMessage(`No log files found for site "${site}".`)
    return
  }
  const choice = await pickLog(logs, `Logs on site ${site}`)
  if (choice) await openLog(site, choice)
}

/** Open the picker scoped to one service. Single log → opens directly. */
export async function showServiceLogs(site: string, service: string): Promise<void> {
  log(`OMD logs: ${site}/${service}`)
  const { logs, failed } = await resolveLogsForService(site, service)
  if (failed) {
    vscode.window.showErrorMessage(
      `Could not read /omd/sites/${site}/var/log. The sudo task was cancelled or failed.`
    )
    return
  }
  if (logs.length === 0) {
    vscode.window.showInformationMessage(`No ${service} logs found on site "${site}".`)
    return
  }
  const choice = await pickLog(logs, `${service} logs on ${site}`)
  if (choice) await openLog(site, choice)
}

/** True if at least one log entry is mapped to this service. */
export function hasLogsForService(service: string): boolean {
  return LOG_CATALOG.some((e) => e.service === service)
}

export function registerLogs(): void {
  // Live tailing is delivered via terminals from openLog(); no document
  // provider or commands need to be registered here.
}
