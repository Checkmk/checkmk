/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log } from '../core/log'
import { safeExec } from '../core/shell'
import { runCommand, waitForTask } from '../core/tasks'
import { versionNewer } from '../core/version'

const PYPI_CHECK_KEY = 'cmk.devSiteTools.lastPypiCheck'
const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000

function getInstalledVersion(): string {
  return safeExec('cmk-dev-install-site --version', { timeout: 3000 })
}

export function isInstalled(): boolean {
  return !!getInstalledVersion()
}

function getLatestPypiVersion(): string {
  const raw = safeExec('curl -s https://pypi.org/pypi/cmk-dev-site/json 2>/dev/null', {
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

  const installed = getInstalledVersion()
  if (!installed) return

  const latest = getLatestPypiVersion()
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

export function getDevSiteToolsState(): DevSiteToolsState {
  const installed = isInstalled()
  const installedVersion = installed ? getInstalledVersion() : ''
  return { installed, installedVersion }
}
