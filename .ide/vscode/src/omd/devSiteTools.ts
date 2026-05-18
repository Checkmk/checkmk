/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { error, log } from '../core/log'
import { loadPersisted, savePersisted } from '../core/persistedCache'
import { safeExecAsync } from '../core/shell'
import { runCommand, waitForTask } from '../core/tasks'
import { versionNewer } from '../core/version'

const PYPI_CHECK_KEY = 'cmk.devSiteTools.lastPypiCheck'
const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000
const DEV_SITE_CACHE_TTL = 5 * 60 * 1000

async function getInstalledVersionAsync(): Promise<string> {
  return safeExecAsync('cmk-dev-install-site --version', { timeout: 3000 })
}

/** Detect whether cmk-dev-install-site is on PATH. Async so we don't stall
 *  vscode.git's SCM view load during extension activation. */
export async function isInstalledAsync(): Promise<boolean> {
  return !!(await getInstalledVersionAsync())
}

async function getLatestPypiVersionAsync(): Promise<string> {
  const raw = await safeExecAsync('curl -s https://pypi.org/pypi/cmk-dev-site/json 2>/dev/null', {
    timeout: 10000
  })
  if (!raw) return ''
  try {
    const data = JSON.parse(raw)
    return data.info?.version || ''
  } catch {
    return ''
  }
}

export async function checkForUpdates(context: vscode.ExtensionContext): Promise<void> {
  const lastCheck = context.globalState.get<number>(PYPI_CHECK_KEY, 0) ?? 0
  if (Date.now() - lastCheck < CHECK_INTERVAL_MS) return

  const installed = await getInstalledVersionAsync()
  if (!installed) return

  const latest = await getLatestPypiVersionAsync()
  if (!latest || !versionNewer(latest, installed)) {
    context.globalState.update(PYPI_CHECK_KEY, Date.now())
    return
  }

  context.globalState.update(PYPI_CHECK_KEY, Date.now())

  log(`cmk-dev-site update available: ${installed} → ${latest}`)
  const choice = await vscode.window.showInformationMessage(
    `cmk-dev-site update available: ${installed} → ${latest}`,
    'Update'
  )
  if (choice === 'Update') {
    log('Update cmk-dev-site')
    const exec = runCommand('cmk-dev-site update', 'pipx upgrade cmk-dev-site')
    if (exec) await waitForTask(exec)
  }
}

export interface DevSiteToolsState {
  installed: boolean
  installedVersion: string
}

const EMPTY_STATE: DevSiteToolsState = { installed: false, installedVersion: '' }
const PERSIST_KEY = 'cmk.devSite.snapshot'

let _stateCache: { state: DevSiteToolsState; timestamp: number } | null = null
let _stateFetchPromise: Promise<void> | null = null
let _onDevSiteRefresh: (() => void) | null = null
let _devSiteHydrated = false

export function setDevSiteRefreshCallback(cb: () => void): void {
  _onDevSiteRefresh = cb
}

function hydrateDevSiteFromPersisted(): void {
  if (_devSiteHydrated) return
  _devSiteHydrated = true
  const persisted = loadPersisted<{ state: DevSiteToolsState; timestamp: number }>(PERSIST_KEY)
  if (persisted) _stateCache = persisted
}

/** Sync getter used during sidebar render. Returns the last known value (or
 *  empty placeholders) immediately and triggers a background refresh that
 *  re-renders the sidebar when the new value lands. */
export function getDevSiteToolsState(): DevSiteToolsState {
  hydrateDevSiteFromPersisted()
  if (_stateCache && Date.now() - _stateCache.timestamp < DEV_SITE_CACHE_TTL) {
    return _stateCache.state
  }
  void scheduleDevSiteRefresh()
  return _stateCache?.state ?? EMPTY_STATE
}

async function scheduleDevSiteRefresh(): Promise<void> {
  if (_stateFetchPromise) return _stateFetchPromise
  _stateFetchPromise = (async () => {
    try {
      const installedVersion = await getInstalledVersionAsync()
      const state: DevSiteToolsState = {
        installed: !!installedVersion,
        installedVersion
      }
      _stateCache = { state, timestamp: Date.now() }
      savePersisted(PERSIST_KEY, _stateCache)
      _onDevSiteRefresh?.()
    } catch (err) {
      error(`devSiteTools refresh failed: ${(err as Error).message}`)
    } finally {
      _stateFetchPromise = null
    }
  })()
  return _stateFetchPromise
}

export function invalidateDevSiteToolsCache(): void {
  _stateCache = null
}
