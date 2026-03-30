/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { log } from '../core/log'
import { safeExec } from '../core/shell'
import { runCommand, waitForTask } from '../core/tasks'

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
  overall: number // 0=running, 1=stopped, 2=partial, -1=unknown
  services: OmdService[]
}

export interface OmdSiteWithStatus extends OmdSite {
  status: OmdStatus
}

// ── Helpers ──

const STATUS_DIR = path.join(os.tmpdir(), 'cmk-omd-status')

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

  const raw = safeExec(`sudo -n omd status --bare "${siteName}" 2>/dev/null`, { timeout: 1000 })
  return parseOmdStatusBare(raw)
}

export async function forceRefreshOmdStatusFiles(): Promise<void> {
  const sites = detectOmdSites()
  let anySucceeded = false
  for (const site of sites) {
    const raw = safeExec(`sudo -n omd status --bare "${site.name}" 2>/dev/null`, { timeout: 1000 })
    if (raw) {
      const statusFile = path.join(STATUS_DIR, `${site.name}.status`)
      try {
        fs.writeFileSync(statusFile, raw)
      } catch {
        /* ignore */
      }
      anySucceeded = true
    }
  }
  if (anySucceeded) return

  const statusCmds = sites
    .map(
      (s) =>
        `sudo omd status --bare "${s.name}" > "${path.join(STATUS_DIR, `${s.name}.status`)}" 2>/dev/null`
    )
    .join(' ; ')
  const exec = runCommand('OMD Status Refresh', statusCmds)
  if (exec) await waitForTask(exec)
}

// ── Create site ──

export async function createSite(): Promise<void> {
  log('Create OMD site wizard')
  const defaultVersion = detectBranchVersion()
  const version = await vscode.window.showInputBox({
    prompt: 'Checkmk version to install',
    placeHolder: 'e.g. 2.5, 2.4.0p9, 2.5.0-daily',
    value: defaultVersion,
    validateInput: (v) => (/^[\w.\-:]+$/.test(v) ? null : 'Invalid version format')
  })
  if (!version) return

  const edition = await vscode.window.showQuickPick(
    [
      { label: 'pro', description: 'Checkmk Pro (default)' },
      { label: 'community', description: 'Checkmk Community' },
      { label: 'cloud', description: 'Checkmk Cloud' },
      { label: 'ultimatemt', description: 'Checkmk MSP' },
      { label: 'ultimate', description: 'Checkmk Ultimate' }
    ],
    { placeHolder: 'Select edition' }
  )
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
    triggerRefresh()
  }
}

function detectBranchVersion(): string {
  const branch = safeExec('git rev-parse --abbrev-ref HEAD 2>/dev/null')
  if (!branch) return ''
  const m = branch.match(/(\d+\.\d+(?:\.\d+)?)/)
  return m ? m[1] : ''
}

// ── Registration ──

let _refreshInterval: ReturnType<typeof setInterval> | null = null
let _onRefresh: (() => void) | null = null

export function registerOmd(context: vscode.ExtensionContext, onRefresh: () => void): void {
  _onRefresh = onRefresh

  const sites = detectOmdSites()
  const available = sites.length > 0
  vscode.commands.executeCommand('setContext', 'cmk.omdAvailable', available)

  if (!available) return

  try {
    fs.mkdirSync(STATUS_DIR, { recursive: true })
  } catch {
    /* ignore */
  }

  const cmds: [string, (site: string) => string][] = [
    ['cmk.omdStart', (site) => `sudo omd start "${site}"`],
    ['cmk.omdStop', (site) => `sudo omd stop "${site}"`],
    ['cmk.omdRestart', (site) => `sudo omd restart "${site}"`]
  ]

  for (const [id, cmdFn] of cmds) {
    context.subscriptions.push(
      vscode.commands.registerCommand(id, async (siteName?: string) => {
        if (!siteName) {
          const pick = await pickSite(sites)
          if (!pick) return
          siteName = pick
        }
        const label = id.replace('cmk.omd', 'OMD ')
        log(`${label}: ${siteName}`)
        const exec = runCommand(`${label} ${siteName}`, cmdFn(siteName))
        if (exec) {
          await waitForTask(exec)
          triggerRefresh()
        }
      })
    )
  }

  let _keepaliveTerm: vscode.Terminal | null = null
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdAuth', () => {
      log('OMD sudo authenticate')
      if (_keepaliveTerm) {
        try {
          _keepaliveTerm.dispose()
        } catch {
          /* ignore */
        }
      }

      const term = vscode.window.createTerminal({ name: 'OMD: sudo keepalive' })
      _keepaliveTerm = term
      term.show()

      const statusCmds = sites
        .map(
          (s) =>
            `sudo omd status --bare "${s.name}" > "${path.join(STATUS_DIR, `${s.name}.status`)}" 2>/dev/null`
        )
        .join(' ; ')

      const loopCmd = [
        `sudo -v && ${statusCmds}`,
        `echo "✓ sudo authenticated — keepalive running (2 min interval, 1h)"`,
        `for i in $(seq 1 30); do sleep 120 && sudo -v && ${statusCmds} && echo "✓ sudo refreshed ($i/30)"; done`,
        `echo "keepalive expired" && exit`
      ].join(' && ')
      term.sendText(loopCmd)

      setTimeout(() => triggerRefresh(), 3000)
      setTimeout(() => triggerRefresh(), 6000)

      const disposable = vscode.window.onDidCloseTerminal((closedTerm) => {
        if (closedTerm === term) {
          disposable.dispose()
          _keepaliveTerm = null
          triggerRefresh()
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

  _refreshInterval = setInterval(() => triggerRefresh(), 30000)
  context.subscriptions.push({
    dispose: () => {
      if (_refreshInterval) clearInterval(_refreshInterval)
    }
  })
}

function triggerRefresh(): void {
  if (_onRefresh) _onRefresh()
}

async function pickSite(sites: OmdSite[]): Promise<string | undefined> {
  const items = sites.map((s) => ({ label: s.name, description: s.version }))
  const pick = await vscode.window.showQuickPick(items, { placeHolder: 'Select OMD site' })
  return pick?.label
}

// ── Service-level commands ──

const ALLOWED_OMD_ACTIONS = new Set(['start', 'stop', 'restart', 'rm', 'status'])

export function omdServiceCommand(
  action: string,
  siteName: string,
  serviceName: string
): ReturnType<typeof runCommand> {
  if (!ALLOWED_OMD_ACTIONS.has(action)) return
  const target = serviceName ? `${serviceName} (${siteName})` : siteName
  const label = `OMD ${action} ${target}`
  const baseCmd = serviceName
    ? `sudo omd ${action} "${siteName}" "${serviceName}"`
    : `sudo omd ${action} "${siteName}"`
  const statusFile = path.join(STATUS_DIR, `${siteName}.status`)
  const cmd = `${baseCmd} ; sudo omd status --bare "${siteName}" > "${statusFile}" 2>/dev/null`
  return runCommand(label, cmd)
}
