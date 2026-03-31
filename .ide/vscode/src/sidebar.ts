/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { checkBuildStatus } from './build/buildStatus'
import type { SettingsEntry } from './build/settings'
import { type ExtensionSets, loadConfig } from './core/config'
import { log, notifyInfo, notifyWarn } from './core/log'
import { runCommand, waitForTask } from './core/tasks'
import { getVersionMismatch, rebuildExtension } from './core/versionCheck'
import { getDevSiteToolsState } from './omd/devSiteTools'
import { detectOmdSites, forceRefreshOmdStatusFiles, getOmdStatus } from './omd/omd'
import { getActiveProxies } from './omd/proxy'
import * as profileManager from './profiles/profileManager'
import * as environmentSection from './sidebar/environment'
import { renderLoading } from './sidebar/html'
import * as ideHealthSection from './sidebar/ideHealth'
import { type IssueItem, IssuesProvider, updateIssues } from './sidebar/issues'
import * as omdSection from './sidebar/omd'
import * as profilesSection from './sidebar/profiles'
import type { SectionModule, StateCache, WebviewMessage } from './sidebar/types'

const SECTIONS = ['environment', 'omd', 'ideHealth', 'profiles'] as const

const sectionModules: Record<string, SectionModule> = {
  environment: environmentSection,
  profiles: profilesSection,
  ideHealth: ideHealthSection,
  omd: omdSection
}

// ── Shared state ──

let _context: vscode.ExtensionContext | null = null
let _onboardingDismissed = false
let _extensionsConfig: ExtensionSets | null = null
let _settingsConfig: Record<string, SettingsEntry> | null = null
let _stateCache: StateCache | null = null
let _commands: Record<string, unknown> | null = null
let _issuesView: vscode.TreeView<IssueItem> | null = null
let _issuesProvider: IssuesProvider | null = null
let _refreshStatusBar: (() => void) | null = null
const _providers: Record<string, SectionViewProvider> = {}

// ── State cache ──

function refreshStateCache(): StateCache {
  _extensionsConfig = loadConfig<ExtensionSets>('extensions')
  _settingsConfig = loadConfig<Record<string, SettingsEntry>>('settings')

  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  const buildStatus = wsPath ? checkBuildStatus(wsPath) : {}
  const profiles = profileManager.getAll()
  const pyEnvsExt = vscode.extensions.getExtension('ms-python.vscode-python-envs')
  const pythonEnvsActive = !!pyEnvsExt && pyEnvsExt.isActive
  const environment = environmentSection.getEnvironmentInfo(wsPath)
  const extensionHealth = ideHealthSection.getExtensionHealth(_extensionsConfig)
  const settingsMismatches = ideHealthSection.getSettingsMismatches(
    _settingsConfig,
    _extensionsConfig
  )
  const omdSites = detectOmdSites().map((site) => {
    const status = getOmdStatus(site.name)
    return { ...site, status }
  })
  const activeProxies = getActiveProxies()
  const devSiteTools = getDevSiteToolsState()
  const versionMismatch = _context ? getVersionMismatch(_context) : null
  const onboarding = environmentSection.getOnboardingState(environment, buildStatus, _context)
  _stateCache = {
    buildStatus,
    profiles,
    commands: _commands || {},
    pythonEnvsActive,
    environment,
    extensionHealth,
    settingsMismatches,
    omdSites,
    activeProxies,
    devSiteTools,
    versionMismatch,
    onboarding,
    onboardingDismissed: _onboardingDismissed
  }

  updateIssues(_issuesView, _issuesProvider, _stateCache)

  return _stateCache
}

// ── Section view provider ──

class SectionViewProvider implements vscode.WebviewViewProvider {
  private _context: vscode.ExtensionContext
  private _section: string
  private _view: vscode.WebviewView | null = null
  private _codiconUri: vscode.Uri | undefined
  private _cspSource: string | undefined

  constructor(context: vscode.ExtensionContext, section: string) {
    this._context = context
    this._section = section
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this._view = webviewView
    const extUri = this._context.extensionUri
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(extUri, 'icons')]
    }
    this._codiconUri = webviewView.webview.asWebviewUri(
      vscode.Uri.joinPath(extUri, 'icons', 'codicon.ttf')
    )
    this._cspSource = webviewView.webview.cspSource

    webviewView.webview.onDidReceiveMessage(
      async (msg: WebviewMessage) => {
        await handleMessage(msg)
      },
      null,
      this._context.subscriptions
    )

    webviewView.onDidChangeVisibility(
      () => {
        if (webviewView.visible) this.refresh()
      },
      null,
      this._context.subscriptions
    )

    this.refresh()
  }

  refresh(): void {
    if (!this._view) return
    const state = _stateCache || refreshStateCache()
    const mod = sectionModules[this._section]
    this._view.webview.html = mod
      ? mod.render(state, this._codiconUri, this._cspSource)
      : renderLoading()
  }

  showLoadingThenRefresh(): void {
    if (!this._view) return
    this._view.webview.html = renderLoading()
    setTimeout(() => this.refresh(), 400)
  }

  showLoading(): void {
    if (!this._view) return
    this._view.webview.html = renderLoading()
  }
}

function showSectionLoading(...sections: string[]): void {
  for (const s of sections) {
    if (_providers[s]) _providers[s].showLoading()
  }
}

// ── Message handling ──

async function handleMessage(msg: WebviewMessage): Promise<void> {
  if (msg.type === 'onboardingDismiss') {
    if (_context) _context.globalState.update('cmk.onboardingDismissed', true)
    _onboardingDismissed = true
    refreshAll()
    return
  }

  if (msg.type === 'refresh') {
    refreshAll()
    return
  }

  const ctx = { refreshAll, showSectionLoading }
  for (const mod of Object.values(sectionModules)) {
    if (await mod.handleMessage(msg, ctx)) return
  }
}

// ── Public API ──

export function refreshAll(): void {
  refreshStateCache()
  for (const p of Object.values(_providers)) {
    p.refresh()
  }
  _refreshStatusBar?.()
}

export function registerSidebar(
  context: vscode.ExtensionContext,
  commands: Record<string, unknown>,
  refreshStatusBar?: () => void
): void {
  _context = context
  _onboardingDismissed = context.globalState.get('cmk.onboardingDismissed', false) as boolean
  _commands = commands
  _refreshStatusBar = refreshStatusBar ?? null
  _extensionsConfig = loadConfig<ExtensionSets>('extensions')
  _settingsConfig = loadConfig<Record<string, SettingsEntry>>('settings')

  for (const section of SECTIONS) {
    const provider = new SectionViewProvider(context, section)
    _providers[section] = provider
    context.subscriptions.push(
      vscode.window.registerWebviewViewProvider(`cmk.dashboard.${section}`, provider, {
        webviewOptions: { retainContextWhenHidden: true }
      })
    )
  }

  _issuesProvider = new IssuesProvider()
  _issuesView = vscode.window.createTreeView('cmk.dashboard.badge', {
    treeDataProvider: _issuesProvider
  })
  context.subscriptions.push(_issuesView)

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.dashboard', () => {
      vscode.commands.executeCommand('cmk.dashboard.environment.focus')
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand(
      'cmk.applySetting',
      async (key: string, expected: unknown, scope: string) => {
        showSectionLoading('ideHealth')
        try {
          await ideHealthSection.writeMismatchSetting(key, expected, scope)
          notifyInfo(`CMK ▸ IDE: Applied ${key}`, `${JSON.stringify(expected)} [${scope}]`)
        } catch (err) {
          notifyWarn(`CMK ▸ IDE: Failed to apply ${key}`, (err as Error).message)
        }
        refreshAll()
      }
    )
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.rebuildExtension', () => {
      rebuildExtension()
    })
  )

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.installDevSite', async () => {
      log('Install cmk-dev-site')
      showSectionLoading('omd')
      const exec = runCommand('Install cmk-dev-site', 'pipx install cmk-dev-site')
      if (exec) {
        await waitForTask(exec)
        vscode.commands.executeCommand('setContext', 'cmk.devSiteInstalled', true)
        refreshAll()
      }
    })
  )

  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (wsPath) {
    const settingsWatcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(wsPath, '.vscode/settings.json')
    )
    settingsWatcher.onDidChange(() => refreshAll())
    settingsWatcher.onDidCreate(() => refreshAll())
    context.subscriptions.push(settingsWatcher)

    const configWatcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(wsPath, '.ide/vscode/config/*.json')
    )
    configWatcher.onDidChange(() => refreshAll())
    configWatcher.onDidCreate(() => refreshAll())
    context.subscriptions.push(configWatcher)
  }

  let configDebounce: ReturnType<typeof setTimeout> | null = null
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(() => {
      if (configDebounce) clearTimeout(configDebounce)
      configDebounce = setTimeout(() => refreshAll(), 500)
    })
  )

  for (const section of SECTIONS) {
    context.subscriptions.push(
      vscode.commands.registerCommand(`cmk.dashboard.refresh.${section}`, async () => {
        const p = _providers[section]
        if (!p) return
        if (section === 'omd') {
          p.showLoading()
          await forceRefreshOmdStatusFiles()
          refreshAll()
          return
        }
        p.showLoadingThenRefresh()
        setTimeout(() => refreshStateCache(), 200)
      })
    )
  }
}
