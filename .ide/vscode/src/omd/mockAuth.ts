/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { probeHttp, waitForHttp } from '../core/http'
import { log, notifyError, notifyInfo, warn } from '../core/log'
import { runCommand } from '../core/tasks'
import type { OmdSite } from './omd'

// Mirrors cmk_dev_site.saas.constants — the mock OIDC provider binds this port
// and answers /healthz. cmk-dev-install-site refuses to create a cloud site
// while the port is free, so the server has to be up before any cloud work.
const OIDC_PORT = 8089
const HEALTH_URL = `http://127.0.0.1:${OIDC_PORT}/healthz`
const MOCK_AUTH_COMMAND = 'cmk-dev-site-mock-auth'
const TASK_NAME = 'OMD: mock auth'

/** Site edition suffixes whose sites authenticate against the mock OIDC provider. */
const CLOUD_EDITIONS = ['cce', 'cloud', 'cse']

export function isCloudSite(site: OmdSite): boolean {
  return CLOUD_EDITIONS.includes(site.edition)
}

export function hasCloudSite(sites: OmdSite[]): boolean {
  return sites.some(isCloudSite)
}

export function isMockAuthRunning(): Promise<boolean> {
  return probeHttp(HEALTH_URL, 1000)
}

/**
 * Launch the mock OIDC provider in a dedicated terminal. It runs in the
 * foreground (uvicorn) and calls `sudo` to write /etc/cse, so it needs a
 * visible terminal the user can type a password into. Resolves once the
 * health endpoint answers, or false if it never came up.
 */
export async function startMockAuth(): Promise<boolean> {
  log(`OMD mock auth: starting ${MOCK_AUTH_COMMAND}`)
  const exec = runCommand(TASK_NAME, MOCK_AUTH_COMMAND, { force: true })
  if (!exec) return false
  const up = await waitForHttp(HEALTH_URL, 60000)
  if (up) {
    log(`OMD mock auth: listening on ${HEALTH_URL}`)
  } else {
    warn(`OMD mock auth: ${HEALTH_URL} did not answer within 60s`)
  }
  return up
}

/** Start the mock auth server unless it already answers. */
export async function ensureMockAuthRunning(): Promise<boolean> {
  if (await isMockAuthRunning()) {
    log('OMD mock auth: already running')
    return true
  }
  return startMockAuth()
}

let _autoStartDone = false

/**
 * Auto-start path: only acts when a cloud/SaaS site exists locally, and only
 * once per session so a failed start doesn't relaunch on every refresh.
 */
async function autoStartForCloudSites(sites: OmdSite[]): Promise<void> {
  if (_autoStartDone) return
  if (!vscode.workspace.getConfiguration('cmk.omd').get<boolean>('autoStartMockAuth', true)) return
  if (!hasCloudSite(sites)) return
  _autoStartDone = true
  if (await isMockAuthRunning()) return
  log('OMD mock auth: cloud site detected, server not running — starting it')
  await startMockAuth()
}

export function registerMockAuth(context: vscode.ExtensionContext, sites: OmdSite[]): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdMockAuth', async () => {
      if (await isMockAuthRunning()) {
        notifyInfo(`CMK: Mock auth server already running on ${HEALTH_URL}`)
        return
      }
      if (await startMockAuth()) {
        notifyInfo(`CMK: Mock auth server running on ${HEALTH_URL}`)
      } else {
        notifyError(`CMK: Mock auth server did not come up on ${HEALTH_URL}`)
      }
    })
  )

  void autoStartForCloudSites(sites)
}
