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
import { type Edition, availableEditions } from '../core/editions'
import { error, log } from '../core/log'
import { safeExecAsync } from '../core/shell'
import { runCommand, waitForTask } from '../core/tasks'
import { promptSocketProxy, registerProxyCleanup } from './proxy'
import {
  BRIDGE_DIR,
  KEEPALIVE_READY,
  clearKeepaliveReady,
  ensureKeepaliveAuth,
  hasKeepalive,
  runInKeepaliveTerminal,
  setKeepaliveTerminal
} from './sudoBridge'

// ── Types ──

export interface OmdSite {
  name: string
  dir: string
  version: string
  port: string
  core: string
  edition: string
}

export interface OmdService {
  name: string
  running: boolean
}

export interface OmdStatus {
  overall: number // 0=running, 1=stopped, 2=partial, 3=disabled, -1=unknown
  services: OmdService[]
}

export interface OmdSiteWithStatus extends OmdSite {
  status: OmdStatus
}

// ── Helpers ──

const STATUS_DIR = path.join(os.tmpdir(), 'cmk-omd-status')

/** Build a `sudo sh -c "..."` command. Arguments are NOT shell-escaped
 *  inside the inner string — callers must only pass safe values (alphanumeric
 *  site names, controlled paths). */
function sudoSh(inner: string): string {
  return `sudo sh -c "${inner.replace(/"/g, '\\"')}"`
}

/**
 * Run a sudo-requiring OMD command through the authenticated keepalive
 * terminal. If no keepalive session is active, auto-prompts the user to
 * authenticate first. Falls back to a dedicated task terminal only if the
 * bridge times out. Returns the exit code, or -1 if the command could not
 * be launched (or the user declined to authenticate).
 */
export async function runOmdSudo(label: string, inner: string): Promise<number> {
  if (!hasKeepalive()) {
    const authed = await ensureKeepaliveAuth()
    if (!authed) return -1
  }
  const bridged = await runInKeepaliveTerminal(inner, 300_000)
  if (bridged) return bridged.exitCode
  const exec = runCommand(label, sudoSh(inner))
  if (!exec) return -1
  const execution = await (exec as unknown as Promise<vscode.TaskExecution>)
  const rc = await waitForTask(execution)
  return rc ?? -1
}

// ── Site discovery (no sudo required) ──

export function detectOmdSites(): OmdSite[] {
  const sitesDir = '/omd/sites'
  if (!fs.existsSync(sitesDir)) return []

  let siteNames: string[]
  try {
    siteNames = fs
      .readdirSync(sitesDir)
      .filter((n) => fs.statSync(path.join(sitesDir, n)).isDirectory())
  } catch {
    return []
  }

  return siteNames.map((name) => {
    const dir = path.join(sitesDir, name)
    const site: OmdSite = { name, dir, version: '', port: '', core: '', edition: '' }

    const infoFile = path.join(dir, 'share', 'omd', 'omd.info')
    try {
      const info = fs.readFileSync(infoFile, 'utf-8')
      const m = info.match(/OMD_VERSION\s*=\s*(.+)/)
      if (m) site.version = m[1].trim()
    } catch {
      /* ignore */
    }

    const confFile = path.join(dir, 'etc', 'omd', 'site.conf')
    try {
      const conf = fs.readFileSync(confFile, 'utf-8')
      const portMatch = conf.match(/CONFIG_APACHE_TCP_PORT='(\d+)'/)
      if (portMatch) site.port = portMatch[1]
      const coreMatch = conf.match(/CONFIG_CORE='(\w+)'/)
      if (coreMatch) site.core = coreMatch[1]
    } catch {
      /* ignore */
    }

    if (site.version) {
      const parts = site.version.split('.')
      const last = parts[parts.length - 1]
      if (['cre', 'cee', 'cce', 'cme', 'pro'].includes(last)) site.edition = last
    }

    return site
  })
}

// ── Site status ──

function parseOmdStatusBare(raw: string): OmdStatus {
  const services: OmdService[] = []
  if (!raw) return { overall: -1, services }
  if (raw.includes('site is disabled')) return { overall: 3, services }

  for (const line of raw.split('\n')) {
    const parts = line.trim().split(/\s+/)
    if (parts.length >= 2) {
      const name = parts[0]
      const status = parseInt(parts[1], 10)
      services.push({ name, running: status === 0 })
    }
  }

  const runCount = services.filter((s) => s.running).length
  let overall: number
  if (services.length === 0) overall = -1
  else if (runCount === services.length) overall = 0
  else if (runCount === 0) overall = 1
  else overall = 2

  return { overall, services }
}

const UNKNOWN_STATUS: OmdStatus = { overall: -1, services: [] }
const SUDO_STATUS_CACHE_TTL = 30 * 1000

interface SudoStatusCacheEntry {
  status: OmdStatus
  timestamp: number
}

const _sudoStatusCache: Map<string, SudoStatusCacheEntry> = new Map()
const _sudoStatusInflight: Map<string, Promise<void>> = new Map()
let _onOmdStatusRefresh: (() => void) | null = null

export function setOmdStatusRefreshCallback(cb: () => void): void {
  _onOmdStatusRefresh = cb
}

export function getOmdStatus(siteName: string): OmdStatus {
  const statusFile = path.join(STATUS_DIR, `${siteName}.status`)
  try {
    const stat = fs.statSync(statusFile)
    if (Date.now() - stat.mtimeMs < 10 * 60 * 1000) {
      const raw = fs.readFileSync(statusFile, 'utf-8').trim()
      if (raw) return parseOmdStatusBare(raw)
    }
  } catch {
    /* ignore */
  }

  const cached = _sudoStatusCache.get(siteName)
  if (cached && Date.now() - cached.timestamp < SUDO_STATUS_CACHE_TTL) {
    return cached.status
  }
  void scheduleSudoStatusRefresh(siteName)
  return cached?.status ?? UNKNOWN_STATUS
}

async function scheduleSudoStatusRefresh(siteName: string): Promise<void> {
  const existing = _sudoStatusInflight.get(siteName)
  if (existing) return existing
  const promise = (async () => {
    try {
      const raw = await safeExecAsync(
        `sudo -n omd status --bare ${shellEscape(siteName)} 2>/dev/null`,
        { timeout: 1000 }
      )
      const status = parseOmdStatusBare(raw)
      _sudoStatusCache.set(siteName, { status, timestamp: Date.now() })
      _onOmdStatusRefresh?.()
    } catch (err) {
      error(`omd status refresh failed for ${siteName}: ${(err as Error).message}`)
    } finally {
      _sudoStatusInflight.delete(siteName)
    }
  })()
  _sudoStatusInflight.set(siteName, promise)
  return promise
}

export async function forceRefreshOmdStatusFiles(): Promise<void> {
  const sites = detectOmdSites()
  if (sites.length === 0) return

  const statusInner = sites
    .map(
      (s) =>
        `omd status --bare ${s.name} > ${path.join(STATUS_DIR, `${s.name}.status`)} 2>&1 || true`
    )
    .join(' ; ')

  // Prefer the keepalive bridge — no new TTY, no re-prompt.
  const bridged = await runInKeepaliveTerminal(statusInner, 10_000)
  if (bridged) return

  const exec = runCommand('OMD Status Refresh', sudoSh(statusInner))
  if (exec) await waitForTask(exec)
}

// ── Create site ──

export async function createSite(): Promise<void> {
  log('Create OMD site wizard')
  const defaultVersion = await detectBranchVersion()
  const version = await vscode.window.showInputBox({
    prompt: 'Checkmk version to install',
    placeHolder: 'e.g. 2.5, 2.4.0p9, 2.5.0-daily',
    value: defaultVersion,
    validateInput: (v) => (/^[\w.\-:]+$/.test(v) ? null : 'Invalid version format')
  })
  if (!version) return

  const editionChoices = [
    { label: 'pro', description: 'Checkmk Pro (default)' },
    { label: 'community', description: 'Checkmk Community' },
    { label: 'cloud', description: 'Checkmk Cloud' },
    { label: 'ultimatemt', description: 'Checkmk MSP' },
    { label: 'ultimate', description: 'Checkmk Ultimate' }
  ].filter((e) => availableEditions().includes(e.label as Edition))
  // On a community-only checkout the list collapses to a single entry — skip the
  // picker and use it directly rather than showing a one-option QuickPick.
  const edition =
    editionChoices.length === 1
      ? editionChoices[0]
      : await vscode.window.showQuickPick(editionChoices, { placeHolder: 'Select edition' })
  if (!edition) return

  const name = await vscode.window.showInputBox({
    prompt: 'Site name (leave empty for auto-generated)',
    placeHolder: `e.g. v${version.replace(/\./g, '').replace(/-.*/, '')}`,
    validateInput: (v) =>
      !v || /^[a-zA-Z0-9_-]+$/.test(v)
        ? null
        : 'Only letters, digits, hyphens, and underscores allowed'
  })

  const dist = await vscode.window.showQuickPick(
    [
      { label: '0', description: 'No distributed sites' },
      { label: '1', description: '1 remote site' },
      { label: '2', description: '2 remote sites' },
      { label: '3', description: '3 remote sites' }
    ],
    { placeHolder: 'Distributed monitoring sites' }
  )
  if (!dist) return

  let cmd = `cmk-dev-install-site ${version} ${edition.label}`
  if (name) cmd += ` -n "${name}"`
  if (dist.label !== '0') cmd += ` -d ${dist.label}`

  log(
    `Create OMD site: ${version} ${edition.label}${name ? ` name=${name}` : ''}${dist.label !== '0' ? ` dist=${dist.label}` : ''}`
  )
  const exec = runCommand(`Create Site: ${version} (${edition.label})`, cmd)
  if (exec) {
    await waitForTask(exec)
    triggerOmdRefresh()
  }
}

async function detectBranchVersion(): Promise<string> {
  const branch = await safeExecAsync('git rev-parse --abbrev-ref HEAD 2>/dev/null')
  if (!branch) return ''
  const m = branch.match(/(\d+\.\d+(?:\.\d+)?)/)
  return m ? m[1] : ''
}

// ── Registration ──

let _refreshInterval: ReturnType<typeof setInterval> | null = null
let _onRefresh: (() => void) | null = null
let _onOmdRefresh: (() => void) | null = null

export function registerOmd(
  context: vscode.ExtensionContext,
  onRefresh: () => void,
  onOmdRefresh?: () => void
): void {
  _onRefresh = onRefresh
  _onOmdRefresh = onOmdRefresh ?? onRefresh

  const initialSites = detectOmdSites()
  vscode.commands.executeCommand('setContext', 'cmk.omdAvailable', initialSites.length > 0)

  registerProxyCleanup(context, onRefresh)

  try {
    fs.mkdirSync(STATUS_DIR, { recursive: true })
  } catch {
    /* ignore */
  }

  const cmds: [string, string][] = [
    ['cmk.omdStart', 'start'],
    ['cmk.omdStop', 'stop'],
    ['cmk.omdRestart', 'restart']
  ]

  for (const [id, action] of cmds) {
    context.subscriptions.push(
      vscode.commands.registerCommand(id, async (siteName?: string) => {
        if (!siteName) {
          const pick = await pickSite(detectOmdSites())
          if (!pick) return
          siteName = pick
        }
        const label = id.replace('cmk.omd', 'OMD ')
        log(`${label}: ${siteName}`)
        await omdServiceCommand(action, siteName, '')
        triggerOmdRefresh()
      })
    )
  }

  try {
    fs.mkdirSync(BRIDGE_DIR, { recursive: true })
  } catch {
    /* ignore */
  }

  let _keepaliveTerm: vscode.Terminal | null = null
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdAuth', () => {
      log('OMD sudo authenticate')
      clearKeepaliveReady()
      if (_keepaliveTerm) {
        try {
          _keepaliveTerm.dispose()
        } catch {
          /* ignore */
        }
      }

      const term = vscode.window.createTerminal({ name: 'OMD: sudo keepalive' })
      _keepaliveTerm = term
      setKeepaliveTerminal(term)
      term.show()

      const sites = detectOmdSites()
      const statusInner = sites
        .map(
          (s) =>
            `omd status --bare ${s.name} > ${path.join(STATUS_DIR, `${s.name}.status`)} 2>&1 || true`
        )
        .join(' ; ')
      const statusCmds = sudoSh(statusInner)

      // Background the refresh loop so the foreground shell returns to an
      // interactive prompt — sendText() can then drive sudo commands without
      // re-prompting (they inherit this TTY's sudo ticket). zsh rejects
      // `cmd & && next`, so wrap the backgrounded subshell in `{ … & }` to
      // produce a compound command with exit status 0 that can chain via &&.
      const loopCmd = [
        `sudo -v`,
        `${statusCmds}`,
        `{ (for i in $(seq 1 30); do sleep 120 && sudo -n -v 2>/dev/null && ${statusCmds}; done) & }`,
        `touch ${shellEscape(KEEPALIVE_READY)}`,
        `echo "✓ sudo authenticated — keepalive running in background (1h). This shell is free for OMD bridge commands."`
      ].join(' && ')
      term.sendText(loopCmd)

      setTimeout(() => triggerOmdRefresh(), 3000)
      setTimeout(() => triggerOmdRefresh(), 6000)

      const disposable = vscode.window.onDidCloseTerminal((closedTerm) => {
        if (closedTerm === term) {
          disposable.dispose()
          _keepaliveTerm = null
          setKeepaliveTerminal(null)
          clearKeepaliveReady()
          triggerOmdRefresh()
        }
      })
      context.subscriptions.push(disposable)
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdOpenBrowser', (siteName: string, port: string) => {
      if (!siteName || !port) return
      log(`OMD open browser: ${siteName}`)
      const url = `http://localhost:${port}/${siteName}/`
      vscode.env.openExternal(vscode.Uri.parse(url))
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdProxy', async () => {
      const siteName = await pickSite(detectOmdSites())
      if (!siteName) return
      await promptSocketProxy(siteName)
      triggerOmdRefresh()
    })
  )

  _refreshInterval = setInterval(() => _onOmdRefresh?.(), 30000)
  context.subscriptions.push({
    dispose: () => {
      if (_refreshInterval) clearInterval(_refreshInterval)
    }
  })
}

export function triggerOmdRefresh(): void {
  if (_onRefresh) _onRefresh()
}

async function pickSite(sites: OmdSite[]): Promise<string | undefined> {
  const items = sites.map((s) => ({ label: s.name, description: s.version }))
  const pick = await vscode.window.showQuickPick(items, { placeHolder: 'Select OMD site' })
  return pick?.label
}

// ── Service-level commands ──

const ALLOWED_OMD_ACTIONS = new Set([
  'start',
  'stop',
  'restart',
  'rm',
  'status',
  'enable',
  'disable'
])

/**
 * Run an OMD action (start/stop/restart/rm/enable/disable) via the sudo
 * bridge when possible, falling back to a task terminal. Returns the exit
 * code of the underlying shell, or -1 if the action couldn't be launched.
 */
export async function omdServiceCommand(
  action: string,
  siteName: string,
  serviceName: string
): Promise<number> {
  if (!ALLOWED_OMD_ACTIONS.has(action)) return -1
  const target = serviceName ? `${serviceName} (${siteName})` : siteName
  const label = `OMD ${action} ${target}`
  let omdAction: string
  if (action === 'enable') {
    omdAction = `omd enable ${siteName}`
  } else if (action === 'disable') {
    omdAction = `omd disable ${siteName}`
  } else if (action === 'rm') {
    omdAction = `omd -f rm ${siteName}`
  } else if (serviceName) {
    omdAction = `omd ${action} ${siteName} ${serviceName}`
  } else {
    omdAction = `omd ${action} ${siteName}`
  }
  const statusFile = path.join(STATUS_DIR, `${siteName}.status`)
  const inner = `${omdAction} ; omd status --bare ${siteName} > ${statusFile} 2>&1 || true`
  return runOmdSudo(label, inner)
}
