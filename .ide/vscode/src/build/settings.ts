/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import {
  type ExtensionSets,
  type SettingValue,
  getExtensionIds,
  resolveVariables
} from '../core/config'
import { runCommand, waitForTask } from '../core/tasks'
import * as profileManager from '../profiles/profileManager'

async function promptReload(message: string): Promise<void> {
  const action = await vscode.window.showInformationMessage(
    `${message} Reload window to apply.`,
    'Reload Now'
  )
  if (action === 'Reload Now') {
    vscode.commands.executeCommand('workbench.action.reloadWindow')
  }
}

const POST_APPLY_HINTS: Record<string, string> = {
  bazel: 'Buildifier may require a full VS Code restart (not just reload) to take effect.'
}

function showPostApplyHints(setName: string): void {
  const hint = POST_APPLY_HINTS[setName]
  if (hint) {
    vscode.window.showWarningMessage(`CMK ▸ IDE: ${hint}`)
  }
}

interface SettingChangeItem extends vscode.QuickPickItem {
  type?: string
  picked?: boolean
  settingKey?: string
  settingValue?: unknown
  settingTarget?: vscode.ConfigurationTarget
}

function collectChanges(
  settings: Record<string, SettingValue>,
  target: vscode.ConfigurationTarget
): { items: SettingChangeItem[]; sameCount: number } {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri
  const resource =
    target === vscode.ConfigurationTarget.WorkspaceFolder ? workspaceFolder : undefined
  const config = vscode.workspace.getConfiguration(undefined, resource)
  const targetLabel =
    target === vscode.ConfigurationTarget.Global
      ? 'user'
      : target === vscode.ConfigurationTarget.Workspace
        ? 'workspace'
        : 'folder'
  const items: SettingChangeItem[] = []
  let sameCount = 0

  for (const [key, rawValue] of Object.entries(settings)) {
    const value = resolveVariables(rawValue)
    const current = config.inspect(key)
    const currentVal =
      target === vscode.ConfigurationTarget.Global
        ? current?.globalValue
        : target === vscode.ConfigurationTarget.Workspace
          ? current?.workspaceValue
          : current?.workspaceFolderValue

    const compactVal = JSON.stringify(value)

    if (currentVal === undefined) {
      items.push({
        type: 'new',
        label: `$(add) [${targetLabel}] ${key}`,
        description: `= ${compactVal.length > 60 ? compactVal.substring(0, 57) + '...' : compactVal}`,
        picked: true,
        settingKey: key,
        settingValue: value,
        settingTarget: target
      })
    } else if (JSON.stringify(currentVal) !== JSON.stringify(value)) {
      const compactOld = JSON.stringify(currentVal)
      items.push({
        type: 'changed',
        label: `$(edit) [${targetLabel}] ${key}`,
        description: `${compactOld.length > 30 ? compactOld.substring(0, 27) + '...' : compactOld} → ${compactVal.length > 30 ? compactVal.substring(0, 27) + '...' : compactVal}`,
        picked: true,
        settingKey: key,
        settingValue: value,
        settingTarget: target
      })
    } else {
      sameCount++
    }
  }

  return { items, sameCount }
}

async function writeSettings(
  settings: Record<string, SettingValue>,
  target: vscode.ConfigurationTarget
): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri
  const resource =
    target === vscode.ConfigurationTarget.WorkspaceFolder ? workspaceFolder : undefined
  const config = vscode.workspace.getConfiguration(undefined, resource)
  for (const [key, rawValue] of Object.entries(settings)) {
    await config.update(key, resolveVariables(rawValue), target)
  }
}

async function runPostApplyHooks(setName: string): Promise<void> {
  if (setName.toLowerCase() === 'cspell') {
    const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
    if (!wsPath) return

    const wsSource = path.join(wsPath, '.ide', 'vscode', 'config', 'checkmk.dict.txt')
    const bundledSource = path.join(__dirname, '..', 'config', 'checkmk.dict.txt')
    const source = fs.existsSync(wsSource) ? wsSource : bundledSource
    const targetDir = path.join(wsPath, '.vscode', '.cspell')
    const target = path.join(targetDir, 'checkmk.dict.txt')

    if (!fs.existsSync(targetDir)) {
      fs.mkdirSync(targetDir, { recursive: true })
    }
    fs.copyFileSync(source, target)
  }
}

export interface SettingsEntry {
  folder?: Record<string, SettingValue>
  workspace?: Record<string, SettingValue>
  user?: Record<string, SettingValue>
}

export function buildEffectiveSettings(
  settingsEntry: SettingsEntry,
  setName: string,
  extensionSets: ExtensionSets | null
): {
  folderSettings: Record<string, SettingValue>
  workspaceSettings: Record<string, SettingValue>
  userSettings: Record<string, SettingValue>
} {
  const folderSettings: Record<string, SettingValue> = { ...(settingsEntry.folder || {}) }
  const workspaceSettings: Record<string, SettingValue> = { ...(settingsEntry.workspace || {}) }
  const userSettings: Record<string, SettingValue> = { ...(settingsEntry.user || {}) }

  if (extensionSets) {
    for (const [family, config] of Object.entries(extensionSets)) {
      if (profileManager.isActive(family)) continue
      const ds = Array.isArray(config) ? {} : config.disableSettings || {}
      for (const [key, value] of Object.entries(ds)) {
        if (key in folderSettings) {
          folderSettings[key] = value as SettingValue
        }
        if (key in workspaceSettings) {
          workspaceSettings[key] = value as SettingValue
        }
      }
    }
  }

  return { folderSettings, workspaceSettings, userSettings }
}

export async function applySettings(
  setName: string,
  settingsEntry: SettingsEntry,
  skipConfirm = false,
  extensionSets: ExtensionSets | null = null
): Promise<void> {
  const { folderSettings, workspaceSettings, userSettings } = buildEffectiveSettings(
    settingsEntry,
    setName,
    extensionSets
  )

  const folderChanges = collectChanges(folderSettings, vscode.ConfigurationTarget.WorkspaceFolder)
  const workspaceChanges = collectChanges(workspaceSettings, vscode.ConfigurationTarget.Workspace)
  const userChanges = collectChanges(userSettings, vscode.ConfigurationTarget.Global)

  const allItems = [...folderChanges.items, ...workspaceChanges.items, ...userChanges.items]
  const totalSame = folderChanges.sameCount + workspaceChanges.sameCount + userChanges.sameCount

  if (allItems.length === 0) {
    vscode.window.showInformationMessage(`CMK ▸ IDE: ${setName} settings are already up to date.`)
    return
  }

  if (!skipConfirm) {
    const newItems = allItems.filter((i) => i.type === 'new')
    const changedItems = allItems.filter((i) => i.type === 'changed')

    const quickPickItems: SettingChangeItem[] = []

    if (newItems.length > 0) {
      quickPickItems.push({ label: 'New Settings', kind: vscode.QuickPickItemKind.Separator })
      quickPickItems.push(...newItems)
    }
    if (changedItems.length > 0) {
      quickPickItems.push({ label: 'Changed Settings', kind: vscode.QuickPickItemKind.Separator })
      quickPickItems.push(...changedItems)
    }
    if (totalSame > 0) {
      quickPickItems.push({ label: 'Info', kind: vscode.QuickPickItemKind.Separator })
      quickPickItems.push({
        label: `$(check) ${totalSame} settings already up to date`,
        description: '',
        alwaysShow: true
      })
    }

    const selectedItems = await new Promise<SettingChangeItem[] | null>((resolve) => {
      let resolved = false
      const picker = vscode.window.createQuickPick<SettingChangeItem>()
      picker.title = `CMK ▸ IDE: ${setName} Settings`
      picker.placeholder = `${newItems.length} new, ${changedItems.length} changed — select settings to apply, then press Enter`
      picker.items = quickPickItems
      picker.selectedItems = quickPickItems.filter((i) => i.picked)
      picker.canSelectMany = true
      picker.matchOnDetail = true

      picker.onDidAccept(() => {
        resolved = true
        const selected = [...picker.selectedItems].filter((i) => i.settingKey)
        picker.hide()
        resolve(selected)
      })

      picker.onDidHide(() => {
        picker.dispose()
        if (!resolved) resolve(null)
      })

      picker.show()
    })

    if (!selectedItems || selectedItems.length === 0) return

    const config = vscode.workspace.getConfiguration(
      undefined,
      vscode.workspace.workspaceFolders?.[0]?.uri
    )
    for (const item of selectedItems) {
      if (item.settingKey && item.settingTarget !== undefined) {
        await config.update(item.settingKey, item.settingValue, item.settingTarget)
      }
    }
    await runPostApplyHooks(setName)
    promptReload(`CMK ▸ IDE: Applied ${selectedItems.length} ${setName} settings.`)
    showPostApplyHints(setName)
    return
  }

  if (Object.keys(folderSettings).length > 0) {
    await writeSettings(folderSettings, vscode.ConfigurationTarget.WorkspaceFolder)
  }
  if (Object.keys(workspaceSettings).length > 0) {
    await writeSettings(workspaceSettings, vscode.ConfigurationTarget.Workspace)
  }
  if (Object.keys(userSettings).length > 0) {
    await writeSettings(userSettings, vscode.ConfigurationTarget.Global)
  }

  await runPostApplyHooks(setName)
  const total =
    Object.keys(folderSettings).length +
    Object.keys(workspaceSettings).length +
    Object.keys(userSettings).length
  promptReload(`CMK ▸ IDE: Applied ${total} ${setName} settings.`)
  showPostApplyHints(setName)
}

export async function installExtensions(setName: string, ids: string[]): Promise<void> {
  const installed: string[] = []
  const alreadyInstalled: string[] = []

  for (const id of ids) {
    const ext = vscode.extensions.getExtension(id)
    if (ext) {
      alreadyInstalled.push(id)
    } else {
      await vscode.commands.executeCommand('workbench.extensions.installExtension', id)
      installed.push(id)
    }
  }

  const parts: string[] = []
  if (installed.length > 0) parts.push(`Installed: ${installed.join(', ')}`)
  if (alreadyInstalled.length > 0) parts.push(`Already installed: ${alreadyInstalled.join(', ')}`)
  vscode.window.showInformationMessage(`CMK ▸ IDE ${setName}: ${parts.join('. ')}`)
}

export function updateContextKeys(extensionSets: ExtensionSets): void {
  for (const setName of Object.keys(extensionSets)) {
    const ids = getExtensionIds(extensionSets, setName)
    const allInstalled = ids.every((id) => vscode.extensions.getExtension(id))
    vscode.commands.executeCommand('setContext', `cmk.${setName}Installed`, allInstalled)
  }
}

export function registerBuildCommands(
  context: vscode.ExtensionContext,
  commands: Record<string, { name: string; command: string; postAction?: string }>
): void {
  for (const [id, entry] of Object.entries(commands)) {
    context.subscriptions.push(
      vscode.commands.registerCommand(id, async () => {
        const execution = await runCommand(entry.name, entry.command)
        if (!execution) return

        if (entry.postAction) {
          const exitCode = await waitForTask(execution)
          if (exitCode === 0) {
            vscode.commands.executeCommand(entry.postAction)
            vscode.window.showInformationMessage(`CMK: ${entry.name} complete.`)
          } else {
            vscode.window.showErrorMessage(`CMK: "${entry.name}" failed (exit code ${exitCode})`)
          }
        }
      })
    )
  }
}
