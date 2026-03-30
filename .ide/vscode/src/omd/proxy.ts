import * as path from 'path'
import * as vscode from 'vscode'

import { log, notifyWarn } from '../core/log'
import { safeExec } from '../core/shell'

// ── Known sockets ──

export const KNOWN_SOCKETS: Record<string, string> = {
  livestatus: 'tmp/run/live',
  redis: 'tmp/run/redis',
  mkeventd: 'tmp/run/mkeventd/status',
  rrdcached: 'tmp/run/rrdcached.sock'
}

const DEFAULT_PORTS: Record<string, string> = {
  livestatus: '6557',
  redis: '6379',
  mkeventd: '6558',
  rrdcached: '6559'
}

// ── Types ──

interface ProxyEntry {
  site: string
  service: string
  socketPath: string
  port: number
  ready: boolean
  terminal: vscode.Terminal
  pollTimer?: ReturnType<typeof setInterval>
}

export interface ProxyInfo {
  site: string
  service: string
  port: number
  ready: boolean
}

// ── State ──

const _activeProxies: ProxyEntry[] = []
let _onRefresh: (() => void) | null = null

// ── Public API ──

export function getActiveProxy(site: string, service: string): ProxyInfo | undefined {
  const entry = _activeProxies.find((p) => p.site === site && p.service === service)
  return entry
    ? { site: entry.site, service: entry.service, port: entry.port, ready: entry.ready }
    : undefined
}

export function getActiveProxies(): ProxyInfo[] {
  return _activeProxies.map((p) => ({
    site: p.site,
    service: p.service,
    port: p.port,
    ready: p.ready
  }))
}

export function startProxy(site: string, service: string, socketPath: string, port: number): void {
  if (!safeExec('which socat')) {
    notifyWarn(
      'CMK ▸ OMD: socat not found',
      'Install socat to use socket proxying: sudo apt install socat'
    )
    return
  }

  const existing = _activeProxies.find((p) => p.port === port)
  if (existing) {
    notifyWarn(
      `CMK ▸ OMD: Port ${port} already in use`,
      `Proxy for ${existing.service}@${existing.site} is using port ${port}`
    )
    return
  }

  log(`Proxy start: ${service}@${site} :${port} → ${socketPath}`)
  const sudoCached = !!safeExec('sudo -n true 2>/dev/null', { timeout: 1000 })
  const socatCmd = `sudo -u "${site}" socat TCP-LISTEN:${port},fork,reuseaddr,bind=127.0.0.1 UNIX-CONNECT:${socketPath}`
  const terminal = vscode.window.createTerminal({
    name: `Proxy: ${service}@${site} :${port}`,
    hideFromUser: sudoCached
  })
  if (!sudoCached) terminal.show(true)
  terminal.sendText(sudoCached ? socatCmd : `sudo -v && ${socatCmd}`)
  const entry: ProxyEntry = { site, service, socketPath, port, ready: false, terminal }
  _activeProxies.push(entry)
  triggerRefresh()

  let polls = 0
  entry.pollTimer = setInterval(() => {
    polls++
    if (safeExec(`ss -tln | grep ':${port} '`, { timeout: 1000 })) {
      entry.ready = true
      if (entry.pollTimer) clearInterval(entry.pollTimer)
      entry.pollTimer = undefined
      triggerRefresh()
    } else if (polls >= 30) {
      if (entry.pollTimer) clearInterval(entry.pollTimer)
      entry.pollTimer = undefined
    }
  }, 1000)
}

export function stopProxy(site: string, service: string): void {
  const idx = _activeProxies.findIndex((p) => p.site === site && p.service === service)
  if (idx === -1) return
  log(`Proxy stop: ${service}@${site}`)
  const entry = _activeProxies[idx]
  if (entry.pollTimer) clearInterval(entry.pollTimer)
  killSocatOnPort(entry.port)
  entry.terminal.dispose()
  _activeProxies.splice(idx, 1)
  triggerRefresh()
}

export function stopAllProxies(): void {
  for (const entry of _activeProxies) {
    try {
      if (entry.pollTimer) clearInterval(entry.pollTimer)
      killSocatOnPort(entry.port)
      entry.terminal.dispose()
    } catch {
      /* ignore */
    }
  }
  _activeProxies.length = 0
}

export function registerProxyCleanup(
  context: vscode.ExtensionContext,
  onRefresh: () => void
): void {
  _onRefresh = onRefresh

  context.subscriptions.push(
    vscode.window.onDidCloseTerminal((closedTerm) => {
      const idx = _activeProxies.findIndex((p) => p.terminal === closedTerm)
      if (idx !== -1) {
        const closed = _activeProxies[idx]
        log(`Proxy terminal closed: ${closed.service}@${closed.site}`)
        if (closed.pollTimer) clearInterval(closed.pollTimer)
        _activeProxies.splice(idx, 1)
        triggerRefresh()
      }
    })
  )

  context.subscriptions.push({ dispose: () => stopAllProxies() })
}

// ── Interactive prompts ──

export async function promptAndStartProxy(
  site: string,
  service: string,
  socketPath: string
): Promise<void> {
  const existing = getActiveProxy(site, service)
  if (existing) {
    const action = await vscode.window.showQuickPick(
      [{ label: 'Stop proxy', description: `:${existing.port}` }, { label: 'Cancel' }],
      { placeHolder: `Proxy for ${service}@${site} is active on port ${existing.port}` }
    )
    if (action?.label === 'Stop proxy') stopProxy(site, service)
    return
  }

  const defaultPort = DEFAULT_PORTS[service] || '9000'
  const portStr = await vscode.window.showInputBox({
    prompt: `TCP port for ${service}@${site} → ${socketPath}`,
    value: defaultPort,
    validateInput: (v) => {
      const n = parseInt(v, 10)
      if (isNaN(n) || n < 1024 || n > 65535) return 'Port must be 1024–65535'
      return null
    }
  })
  if (!portStr) return
  startProxy(site, service, socketPath, parseInt(portStr, 10))
}

export async function promptSocketProxy(site: string): Promise<void> {
  const items = Object.entries(KNOWN_SOCKETS).map(([name, rel]) => ({
    label: name,
    description: rel
  }))
  items.push({ label: 'Custom path…', description: 'Enter a custom socket path' })

  const pick = await vscode.window.showQuickPick(items, {
    placeHolder: `Select socket for site "${site}"`
  })
  if (!pick) return

  let service: string
  let socketPath: string
  if (pick.label === 'Custom path…') {
    const custom = await vscode.window.showInputBox({
      prompt: 'Full path to Unix socket',
      placeHolder: `/omd/sites/${site}/tmp/run/...`
    })
    if (!custom) return
    service = path.basename(custom)
    socketPath = custom
  } else {
    service = pick.label
    socketPath = path.join('/omd/sites', site, KNOWN_SOCKETS[service])
  }

  await promptAndStartProxy(site, service, socketPath)
}

// ── Internal ──

function killSocatOnPort(port: number): void {
  const pid = safeExec(`sudo lsof -ti TCP:${port} -sTCP:LISTEN`, { timeout: 3000 })
  if (pid) {
    for (const p of pid.split('\n').filter(Boolean)) {
      safeExec(`sudo kill ${p}`, { timeout: 2000 })
    }
  }
}

function triggerRefresh(): void {
  if (_onRefresh) _onRefresh()
}
