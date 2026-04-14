/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { type CommandEntry, createStatusBar } from './build/buildStatus'
import { type SettingsEntry, registerBuildCommands, updateContextKeys } from './build/settings'
import {
  type ExtensionSets,
  type ScopedSetting,
  getDisableSettings,
  loadConfig,
  writeSetting
} from './core/config'
import { error, log, notifyInfo, registerErrorHandlers } from './core/log'
import { checkVersionMismatch } from './core/versionCheck'
import { registerGerritPush } from './gerrit'
import { checkForUpdates, isInstalled as isDevSiteInstalled } from './omd/devSiteTools'
import { registerLogs } from './omd/logs'
import { createSite, registerOmd } from './omd/omd'
import {
  generatePrettierConfig,
  registerPrettierConfigWatcher
} from './profiles/frontend/prettierConfig'
import { registerProfileDetector } from './profiles/profileDetector'
import * as profileManager from './profiles/profileManager'
import { registerBazelTestRunner } from './profiles/python/bazelTest'
import { registerInterpreterResolver } from './profiles/python/interpreter'
// Family-gated modules
import {
  generateAndWriteMypyConfig,
  killAllDmypyDaemons,
  registerMypyConfigWatcher
} from './profiles/python/mypyConfig'
import { registerSnippets } from './profiles/python/snippets'
import { registerIdePickers } from './setup/idePicker'
import { registerTemplates } from './setup/templates'
import { refreshAll, refreshOmd, registerSidebar } from './sidebar'

function toggleSettings(disableSettings: ScopedSetting[]): vscode.Disposable {
  ;(async () => {
    try {
      for (const { key, value: disabledValue, target } of disableSettings) {
        const dot = key.lastIndexOf('.')
        let currentValue: unknown
        if (dot > 0) {
          const section = key.substring(0, dot)
          const leaf = key.substring(dot + 1)
          currentValue = vscode.workspace.getConfiguration(section).get(leaf)
        } else {
          currentValue = vscode.workspace.getConfiguration().get(key)
        }
        if (JSON.stringify(currentValue) === JSON.stringify(disabledValue)) {
          await writeSetting(key, undefined, target)
        }
      }
    } catch (err) {
      error(`Failed to remove disable-settings: ${(err as Error).message}`)
    }
  })()
  return {
    dispose: () => {
      ;(async () => {
        try {
          for (const { key, value, target } of disableSettings) {
            await writeSetting(key, value, target)
          }
        } catch (err) {
          error(`Failed to write disable-settings: ${(err as Error).message}`)
        }
      })()
    }
  }
}

export function activate(context: vscode.ExtensionContext): void {
  log('Extension activating')
  registerErrorHandlers()
  const commands = loadConfig<Record<string, CommandEntry>>('commands')
  const extensionSets = loadConfig<ExtensionSets>('extensions')
  const settingsSets = loadConfig<Record<string, SettingsEntry>>('settings')

  // --- Always-on features ---

  const cmkLogo = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 54)
  cmkLogo.text = '$(cmk-logo)'
  cmkLogo.tooltip = 'Checkmk — Dashboard'
  cmkLogo.command = 'cmk.dashboard.environment.focus'
  cmkLogo.color = new vscode.ThemeColor('cmk.logoColor')
  cmkLogo.show()
  context.subscriptions.push(cmkLogo)

  const { refreshStatus } = createStatusBar(context, commands, refreshAll)
  registerSidebar(context, commands, refreshStatus)
  registerTemplates(context)
  registerBuildCommands(context, commands)
  registerIdePickers(context, extensionSets, settingsSets)
  registerGerritPush(context)
  registerOmd(context, refreshAll, refreshOmd)
  registerLogs()

  // cmk-dev-site: create site command + update check
  vscode.commands.executeCommand('setContext', 'cmk.devSiteInstalled', isDevSiteInstalled())
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdCreateSite', () => {
      log('Create OMD site')
      return createSite()
    })
  )
  checkForUpdates(context)

  // Config regeneration commands
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (wsPath) {
    context.subscriptions.push(
      vscode.commands.registerCommand('cmk.regenerateMypyConfig', async () => {
        const changed = await generateAndWriteMypyConfig(wsPath)
        if (changed) {
          notifyInfo('CMK: Regenerated .vscode/.mypy.ini from pyproject.toml')
        } else {
          notifyInfo('CMK: .vscode/.mypy.ini is already up to date')
        }
      }),
      vscode.commands.registerCommand('cmk.regeneratePrettierConfig', () => {
        generatePrettierConfig(wsPath)
        notifyInfo('CMK: Regenerated .vscode/.prettier.config.cjs')
      })
    )
  }

  updateContextKeys(extensionSets)
  context.subscriptions.push(
    vscode.extensions.onDidChange(() => {
      updateContextKeys(extensionSets)
      refreshAll()
    })
  )

  // --- Family-gated features ---

  const pythonDisable = getDisableSettings('python')
  profileManager.register(
    'python',
    () => {
      return [
        ...registerMypyConfigWatcher(),
        ...registerInterpreterResolver(),
        ...registerSnippets(),
        ...registerBazelTestRunner(),
        toggleSettings(pythonDisable),
        { dispose: () => killAllDmypyDaemons() },
        {
          dispose: () => {
            setTimeout(() => vscode.commands.executeCommand('testing.refreshTests'), 500)
          }
        }
      ]
    },
    pythonDisable
  )

  const frontendDisable = getDisableSettings('frontend')
  profileManager.register(
    'frontend',
    () => {
      return [...registerPrettierConfigWatcher(), toggleSettings(frontendDisable)]
    },
    frontendDisable
  )

  const rustDisable = getDisableSettings('rust')
  profileManager.register(
    'rust',
    () => {
      return [
        toggleSettings(rustDisable),
        {
          dispose: () => {
            vscode.commands.executeCommand('rust-analyzer.stopServer')
            setTimeout(() => vscode.commands.executeCommand('testing.refreshTests'), 500)
          }
        }
      ]
    },
    rustDisable
  )

  profileManager.setOnRefresh(refreshAll)
  profileManager.init(context)
  registerProfileDetector(context)
  checkVersionMismatch(context)

  // --- First-run wizard ---
  const SETUP_DONE_KEY = 'cmk.setupWizardDismissed'
  if (!context.globalState.get(SETUP_DONE_KEY)) {
    const config = vscode.workspace.getConfiguration(
      undefined,
      vscode.workspace.workspaceFolders?.[0]?.uri
    )
    const hasGeneralSettings =
      config.inspect('editor.formatOnSave')?.workspaceFolderValue !== undefined
    const hasBranchProtection =
      config.inspect('git.branchProtection')?.workspaceFolderValue !== undefined

    if (!hasGeneralSettings || !hasBranchProtection) {
      vscode.window
        .showInformationMessage(
          'CMK: First time? Open the dashboard to get started with system setup, venv build, and IDE configuration.',
          'Open Dashboard',
          'Not Now',
          "Don't Ask Again"
        )
        .then((choice) => {
          if (choice === 'Open Dashboard') {
            vscode.commands.executeCommand('cmk.dashboard.environment.focus')
          } else if (choice === "Don't Ask Again") {
            context.globalState.update(SETUP_DONE_KEY, true)
          }
        })
    } else {
      context.globalState.update(SETUP_DONE_KEY, true)
    }
  }
}

export function deactivate(): void {}
