/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { registerStartupBenchmarks } from './benchmark/startup'
import { registerBazelCache } from './build/bazelCache'
import { type CommandEntry, createStatusBar } from './build/buildStatus'
import { type SettingsEntry, registerBuildCommands, updateContextKeys } from './build/settings'
import {
  type ExtensionSets,
  type ScopedSetting,
  getDisableSettings,
  getEnableSettings,
  loadConfig,
  writeSetting
} from './core/config'
import { error, log, notifyInfo, registerErrorHandlers } from './core/log'
import { bindPersistedCacheContext } from './core/persistedCache'
import { checkVersionMismatch } from './core/versionCheck'
import { deployToSite } from './omd/devDeployTools'
import { checkForUpdates, isInstalledAsync as isDevSiteInstalledAsync } from './omd/devSiteTools'
import { registerLogs } from './omd/logs'
import { createSite, detectOmdSites, registerOmd } from './omd/omd'
import { registerProfileDetector } from './profiles/profileDetector'
import * as profileManager from './profiles/profileManager'
import { registerDmypyHealth } from './profiles/python/dmypyHealth'
import { registerDynamicMypyTargets } from './profiles/python/dynamicMypyTargets'
import { registerInterpreterResolver } from './profiles/python/interpreter'
import { registerJemallocAllocator } from './profiles/python/jemallocAllocator'
// Family-gated modules
import {
  generateAndWriteMypyConfig,
  killAllDmypyDaemons,
  registerMypyConfigWatcher
} from './profiles/python/mypyConfig'
import { registerPylanceHealth } from './profiles/python/pylanceHealth'
import { registerSnippets } from './profiles/python/snippets'
import { registerGerritPush, registerSandboxBranch, registerScm } from './scm'
import { registerGitFixers } from './scm/gitState'
import { registerIdePickers } from './setup/idePicker'
import { registerTemplates } from './setup/templates'
import { refreshAll, refreshOmd, registerSidebar } from './sidebar'
import { registerBazelTestRunner } from './testing/bazelTest'
import { registerBazelTestController } from './testing/bazelTestController'
import { registerBazelTestsConfigView } from './testing/bazelTestsConfigView'
import { registerWhatsNew, showWhatsNewIfNeeded } from './whatsNew'

function toggleSettings(
  disableSettings: ScopedSetting[],
  enableSettings: ScopedSetting[] = []
): vscode.Disposable {
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
      for (const { key, value, target } of enableSettings) {
        await writeSetting(key, value, target)
      }
    } catch (err) {
      error(`Failed to apply profile-active settings: ${(err as Error).message}`)
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
  bindPersistedCacheContext(context)
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
  registerScm(context)
  context.subscriptions.push(...registerGitFixers())
  context.subscriptions.push(...registerBazelCache())
  registerSandboxBranch(context)
  registerOmd(context, refreshAll, refreshOmd)
  registerLogs()

  // cmk-dev-site: create site command + update check
  // Detect cmk-dev-install-site asynchronously so the up-to-3s subprocess
  // call doesn't block activate() — and with it the rest of the extension
  // host, including vscode.git's SCM view loading.
  void isDevSiteInstalledAsync().then((installed) => {
    vscode.commands.executeCommand('setContext', 'cmk.devSiteInstalled', installed)
  })
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdCreateSite', () => {
      log('Create OMD site')
      return createSite()
    })
  )
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.omdDeploy', async (siteArg?: string) => {
      let siteName = siteArg
      if (!siteName) {
        const sites = detectOmdSites()
        const pick = await vscode.window.showQuickPick(
          sites.map((s) => ({ label: s.name, description: s.version })),
          { placeHolder: 'Select OMD site to deploy to' }
        )
        if (!pick) return
        siteName = pick.label
      }
      await deployToSite(siteName)
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

  // Bazel test discovery + runner — deferred until the first Python /
  // TypeScript editor activates, or 10 s elapse, whichever fires first. The
  // test controller's own discovery is already lazy, but the registration
  // itself does enough work to be worth keeping off the activate() path.
  let bazelTestsRegistered = false
  const registerBazelTestsOnce = (): void => {
    if (bazelTestsRegistered) return
    bazelTestsRegistered = true
    disposeBazelTestsTriggers()
    context.subscriptions.push(...registerBazelTestController(), ...registerBazelTestsConfigView())
  }
  const bazelTestsTriggers: vscode.Disposable[] = []
  const disposeBazelTestsTriggers = (): void => {
    for (const d of bazelTestsTriggers) {
      try {
        d.dispose()
      } catch {
        // ignore
      }
    }
  }
  bazelTestsTriggers.push(
    vscode.window.onDidChangeActiveTextEditor((ed) => {
      if (!ed) return
      const lang = ed.document.languageId
      if (lang === 'python' || lang === 'typescript' || lang === 'typescriptreact')
        registerBazelTestsOnce()
    })
  )
  const bazelTestsFallback = setTimeout(registerBazelTestsOnce, 10_000)
  bazelTestsTriggers.push({ dispose: () => clearTimeout(bazelTestsFallback) })
  context.subscriptions.push(...bazelTestsTriggers)

  // --- Family-gated features ---

  const pythonDisable = getDisableSettings('python')
  const pythonEnable = getEnableSettings('python')
  profileManager.register(
    'python',
    () => {
      return [
        ...registerDynamicMypyTargets(context),
        ...registerJemallocAllocator(context),
        ...registerPylanceHealth(refreshAll),
        ...registerMypyConfigWatcher(),
        ...registerDmypyHealth(),
        ...registerInterpreterResolver(),
        ...registerSnippets(),
        ...registerBazelTestRunner(),
        vscode.commands.registerCommand('cmk.python.restartLanguageServer', () =>
          vscode.commands.executeCommand('python.analysis.restartLanguageServer')
        ),
        toggleSettings(pythonDisable, pythonEnable),
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
  const frontendEnable = getEnableSettings('frontend')
  profileManager.register(
    'frontend',
    () => {
      return [toggleSettings(frontendDisable, frontendEnable)]
    },
    frontendDisable
  )

  const rustDisable = getDisableSettings('rust')
  const rustEnable = getEnableSettings('rust')
  profileManager.register(
    'rust',
    () => {
      return [
        toggleSettings(rustDisable, rustEnable),
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

  const cppDisable = getDisableSettings('cpp')
  const cppEnable = getEnableSettings('cpp')
  profileManager.register(
    'cpp',
    () => {
      return [toggleSettings(cppDisable, cppEnable)]
    },
    cppDisable
  )

  profileManager.setOnRefresh(refreshAll)
  profileManager.init(context)
  registerProfileDetector(context)

  context.subscriptions.push(...registerWhatsNew(context))

  // Defer the version-mismatch dialog and the What's New popup by 2 s —
  // neither needs to land before the user can interact, and both can pop
  // blocking modals that drag the perceived activate path.
  const deferred = setTimeout(() => {
    checkVersionMismatch(context)
    showWhatsNewIfNeeded(context).catch((err) =>
      error(`What's new failed: ${(err as Error).message}`)
    )
  }, 2000)
  context.subscriptions.push({ dispose: () => clearTimeout(deferred) })

  context.subscriptions.push(...registerStartupBenchmarks(context))

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
