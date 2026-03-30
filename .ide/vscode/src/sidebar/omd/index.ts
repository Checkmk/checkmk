/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as path from 'path'
import * as vscode from 'vscode'

import { log } from '../../core/log'
import { runCommand, waitForTask } from '../../core/tasks'
import { createSite, omdServiceCommand } from '../../omd/omd'
import { KNOWN_SOCKETS, promptAndStartProxy, promptSocketProxy, stopProxy } from '../../omd/proxy'
import { esc, getNonce, wrap } from '../html'
import type { SectionContext, StateCache, WebviewMessage } from '../types'
import sectionCss from './style.css'

export async function handleMessage(
  msg: WebviewMessage,
  { refreshAll, showSectionLoading }: SectionContext
): Promise<boolean> {
  switch (msg.type) {
    case 'omdSiteAction': {
      log(`OMD site ${msg.action}: ${msg.site}`)
      showSectionLoading('omd')
      const exec = omdServiceCommand(msg.action as string, msg.site as string, '')
      if (exec) {
        await waitForTask(exec)
        refreshAll()
      }
      return true
    }
    case 'omdServiceAction': {
      log(`OMD service ${msg.action}: ${msg.service} on ${msg.site}`)
      showSectionLoading('omd')
      const exec = omdServiceCommand(
        msg.action as string,
        msg.site as string,
        msg.service as string
      )
      if (exec) {
        await waitForTask(exec)
        refreshAll()
      }
      return true
    }
    case 'omdOpenBrowser': {
      log(`OMD open browser: ${msg.url}`)
      const url = msg.url
      if (typeof url === 'string' && /^https?:\/\/localhost[:/]/.test(url)) {
        vscode.env.openExternal(vscode.Uri.parse(url))
      }
      return true
    }
    case 'omdConsole': {
      log(`OMD console: ${msg.site}`)
      const term = vscode.window.createTerminal({ name: `OMD: ${msg.site}` })
      term.show()
      term.sendText(`sudo omd su "${msg.site}"`)
      return true
    }
    case 'omdAuth':
      log('OMD authenticate')
      vscode.commands.executeCommand('cmk.omdAuth')
      return true
    case 'omdCreateSite':
      log('OMD create site')
      await createSite()
      refreshAll()
      return true
    case 'omdInstallDevSite': {
      log('Install cmk-dev-site')
      showSectionLoading('omd')
      const exec = runCommand('Install cmk-dev-site', 'pipx install cmk-dev-site')
      if (exec) {
        await waitForTask(exec)
        vscode.commands.executeCommand('setContext', 'cmk.devSiteInstalled', true)
        refreshAll()
      }
      return true
    }
    case 'omdProxyStart': {
      const service = msg.service as string
      const socketRel = KNOWN_SOCKETS[service]
      if (!socketRel) return true
      const socketPath = path.join('/omd/sites', msg.site as string, socketRel)
      await promptAndStartProxy(msg.site as string, service, socketPath)
      refreshAll()
      return true
    }
    case 'omdProxyStop': {
      stopProxy(msg.site as string, msg.service as string)
      refreshAll()
      return true
    }
    case 'omdProxySite': {
      await promptSocketProxy(msg.site as string)
      refreshAll()
      return true
    }
    case 'omdDeleteSite': {
      log(`OMD delete site: ${msg.site}`)
      const confirm = await vscode.window.showWarningMessage(
        `Delete OMD site "${msg.site}"? This will permanently remove ALL site data.`,
        { modal: true },
        'Delete'
      )
      if (confirm === 'Delete') {
        showSectionLoading('omd')
        const exec = omdServiceCommand('rm', msg.site as string, '')
        if (exec) {
          await waitForTask(exec)
          refreshAll()
        }
      }
      return true
    }
    default:
      return false
  }
}

export function render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const { omdSites, activeProxies, devSiteTools } = state

  const devSiteBanner = !devSiteTools?.installed
    ? `<div class="banner banner-info">
        <span>cmk-dev-site not installed — required for site creation.</span>
        <button class="btn btn-small" data-action="omd-install-devsite"><span class="codicon codicon-package"></span> Install</button>
      </div>`
    : ''

  if (!omdSites || omdSites.length === 0) {
    const createBtn = devSiteTools?.installed
      ? `<div style="margin-top:8px"><button class="btn btn-small" data-action="omd-create-site"><span class="codicon codicon-add"></span> Create Site</button></div>`
      : ''
    return wrap(
      nonce,
      sectionCss,
      devSiteBanner +
        `<div class="card"><span class="card-label">No OMD sites found</span></div>` +
        createBtn,
      codiconUri,
      cspSource
    )
  }

  const needsAuth = omdSites.some((s) => s.status.overall === -1)
  const authBanner = needsAuth
    ? `<div class="banner banner-warn">
        <span>sudo credentials not cached — service status unavailable.</span>
        <button class="btn btn-small" data-action="omd-auth"><span class="codicon codicon-shield"></span> Authenticate (YubiKey)</button>
       </div>`
    : ''

  const statusLabel = (o: number) =>
    o === 0 ? 'running' : o === 1 ? 'stopped' : o === 2 ? 'partial' : 'unknown'
  const statusIcon = (o: number) =>
    o === 0 ? '&#10003;' : o === 1 ? '&#10007;' : o === 2 ? '&#9888;' : '&#63;'
  const statusCls = (o: number) =>
    o === 0 ? 'ok' : o === 1 ? 'error' : o === 2 ? 'stale' : 'unknown'

  const sites = omdSites
    .map((site) => {
      const o = site.status.overall
      const cls = statusCls(o)
      const icon = statusIcon(o)
      const badge = `<span class="card-badge omd-badge-${cls}">${statusLabel(o)}</span>`
      const browserBtn = site.port
        ? `<button class="btn btn-small btn-icon" data-action="omd-open-browser" data-url="http://localhost:${esc(site.port)}/${esc(site.name)}/" title="Open in browser"><span class="codicon codicon-link-external"></span></button>`
        : ''
      const isRunning = o === 0 || o === 2
      const toggleAction = isRunning ? 'stop' : 'start'
      const toggleIcon = isRunning ? 'codicon-debug-stop' : 'codicon-play'
      const toggleTitle = isRunning ? 'Stop site' : 'Start site'
      const toggleBtn =
        o !== -1
          ? `<button class="btn btn-small btn-icon" data-action="omd-site-action" data-omd-action="${toggleAction}" data-site="${esc(site.name)}" title="${toggleTitle}"><span class="codicon ${toggleIcon}"></span></button>`
          : ''
      const proxyBtn = isRunning
        ? `<button class="btn btn-small btn-icon" data-action="omd-proxy-site" data-site="${esc(site.name)}" title="Socket proxy"><span class="codicon codicon-debug-disconnect"></span></button>`
        : ''
      const consoleBtn = `<button class="btn btn-small btn-icon" data-action="omd-console" data-site="${esc(site.name)}" title="Open site console"><span class="codicon codicon-terminal"></span></button>`
      const deleteBtn = `<button class="btn btn-small btn-icon btn-danger" data-action="omd-delete-site" data-site="${esc(site.name)}" title="Delete site"><span class="codicon codicon-trash"></span></button>`
      const svcRows = site.status.services
        .map((svc) => {
          const sIcon = svc.running ? '&#9679;' : '&#9675;'
          const sCls = svc.running ? 'svc-running' : 'svc-stopped'
          const hasSocket = svc.name in KNOWN_SOCKETS
          const proxy = activeProxies.find((p) => p.site === site.name && p.service === svc.name)
          let proxyBtn = ''
          if (svc.running && hasSocket) {
            if (proxy) {
              const badgeCls = proxy.ready ? 'proxy-badge' : 'proxy-badge proxy-badge-starting'
              proxyBtn = `<button class="${badgeCls}" data-action="omd-proxy-stop" data-site="${esc(site.name)}" data-service="${esc(svc.name)}" title="Stop proxy :${proxy.port}">:${proxy.port} <span class="codicon codicon-debug-stop"></span></button>`
            } else {
              proxyBtn = `<button class="btn btn-small btn-icon" data-action="omd-proxy-start" data-site="${esc(site.name)}" data-service="${esc(svc.name)}" title="Socket proxy"><span class="codicon codicon-debug-disconnect"></span></button>`
            }
          }
          const actions = svc.running
            ? `<button class="btn btn-small btn-icon" data-action="omd-service-action" data-omd-action="stop" data-site="${esc(site.name)}" data-service="${esc(svc.name)}" title="Stop"><span class="codicon codicon-debug-stop"></span></button><button class="btn btn-small btn-icon" data-action="omd-service-action" data-omd-action="restart" data-site="${esc(site.name)}" data-service="${esc(svc.name)}" title="Restart"><span class="codicon codicon-debug-restart"></span></button>`
            : `<button class="btn btn-small btn-icon" data-action="omd-service-action" data-omd-action="start" data-site="${esc(site.name)}" data-service="${esc(svc.name)}" title="Start"><span class="codicon codicon-play"></span></button>`
          return `<div class="svc-row ${sCls}"><span class="svc-icon">${sIcon}</span><span class="svc-name">${esc(svc.name)}</span><span class="svc-actions">${proxyBtn}${actions}</span></div>`
        })
        .join('')
      const siteActions = `<div class="omd-site-actions">
      <button class="btn btn-small" data-action="omd-site-action" data-omd-action="start" data-site="${esc(site.name)}"><span class="codicon codicon-run-all"></span> Start All</button>
      <button class="btn btn-small" data-action="omd-site-action" data-omd-action="stop" data-site="${esc(site.name)}"><span class="codicon codicon-debug-stop"></span> Stop All</button>
      <button class="btn btn-small" data-action="omd-site-action" data-omd-action="restart" data-site="${esc(site.name)}"><span class="codicon codicon-debug-restart"></span> Restart All</button>
    </div>`
      const detail = `<span class="omd-detail">${esc(site.version)}${site.core ? ' · ' + esc(site.core) : ''}</span>`
      return `<div class="omd-site">
      <div class="omd-site-header ${cls}" data-action="toggle-accordion">
        <span class="card-icon">${icon}</span>
        <span class="omd-site-name">${esc(site.name)}</span>
        ${detail}
        ${badge}
        ${toggleBtn}
        ${proxyBtn}
        ${consoleBtn}
        ${browserBtn}
        ${deleteBtn}
        <span class="ext-chevron codicon codicon-chevron-right"></span>
      </div>
      <div class="omd-site-body">
        ${svcRows}
        ${siteActions}
      </div>
    </div>`
    })
    .join('')

  return wrap(nonce, sectionCss, devSiteBanner + authBanner + sites, codiconUri, cspSource)
}
