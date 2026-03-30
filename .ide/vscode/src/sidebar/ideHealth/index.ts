/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { type SettingsEntry, buildEffectiveSettings } from '../../build/settings'
import { type ExtensionSets, loadConfig, resolveVariables } from '../../core/config'
import { FAMILY_DISPLAY } from '../../core/constants'
import { log, notifyInfo, notifyWarn } from '../../core/log'
import * as profileManager from '../../profiles/profileManager'
import { esc, getNonce, wrap } from '../html'
import type {
  ExtensionFamily,
  SectionContext,
  SettingsMismatch,
  StateCache,
  WebviewMessage
} from '../types'
import sectionCss from './style.css'

export function getExtensionHealth(extensionsConfig?: ExtensionSets | null): ExtensionFamily[] {
  const extensionSets: ExtensionSets = extensionsConfig || loadConfig<ExtensionSets>('extensions')
  const families: ExtensionFamily[] = []
  for (const [family, config] of Object.entries(extensionSets)) {
    const extIds = Array.isArray(config) ? config : config.extensions || []
    if (extIds.length === 0) continue
    const extensions = extIds.map((id) => ({ id, installed: !!vscode.extensions.getExtension(id) }))
    families.push({
      name: family,
      displayName: FAMILY_DISPLAY[family] || family,
      required: !Array.isArray(config) && config.required === true,
      extensions,
      allInstalled: extensions.every((e) => e.installed),
      installedCount: extensions.filter((e) => e.installed).length
    })
  }
  return families
}

export function getSettingsMismatches(
  settingsConfig?: Record<string, SettingsEntry> | null,
  extensionsConfig?: ExtensionSets | null
): SettingsMismatch[] {
  const settingsSets: Record<string, SettingsEntry> =
    settingsConfig || loadConfig<Record<string, SettingsEntry>>('settings')
  const extensionSets: ExtensionSets = extensionsConfig || loadConfig<ExtensionSets>('extensions')
  const mismatches: SettingsMismatch[] = []

  const isFolderWorkspace = vscode.workspace.workspaceFile === undefined

  type Inspection = ReturnType<vscode.WorkspaceConfiguration['inspect']>
  const SCOPE_CONFIG = [
    {
      scope: 'folder' as const,
      label: 'folder',
      getter: (i: Inspection) => i?.workspaceFolderValue
    },
    {
      scope: 'workspace' as const,
      label: 'workspace',
      getter: (i: Inspection) =>
        i?.workspaceValue ?? (isFolderWorkspace ? i?.workspaceFolderValue : undefined)
    },
    { scope: 'user' as const, label: 'user', getter: (i: Inspection) => i?.globalValue }
  ]

  const seen = new Set<string>()

  for (const [family, settingsEntry] of Object.entries(settingsSets)) {
    const displayName = FAMILY_DISPLAY[family] || family
    const { folderSettings, workspaceSettings, userSettings } = buildEffectiveSettings(
      settingsEntry,
      family,
      extensionSets
    )

    const scopeSettings = {
      folder: folderSettings,
      workspace: workspaceSettings,
      user: userSettings
    }

    for (const { scope, label, getter } of SCOPE_CONFIG) {
      const settings = scopeSettings[scope]
      if (!settings || Object.keys(settings).length === 0) continue

      const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri
      const resource = scope === 'folder' ? wsFolder : undefined
      const cfg = vscode.workspace.getConfiguration(undefined, resource)

      for (const [key, rawExpected] of Object.entries(settings)) {
        const dedupeKey = `${key}@${label}`
        if (seen.has(dedupeKey)) continue
        seen.add(dedupeKey)

        const expected = resolveVariables(rawExpected)
        const inspection = cfg.inspect(key)
        const actual = getter(inspection)

        if (actual === undefined) {
          mismatches.push({ key, expected, actual: undefined, family: displayName, scope: label })
        } else if (JSON.stringify(actual) !== JSON.stringify(expected)) {
          mismatches.push({ key, expected, actual, family: displayName, scope: label })
        }
      }
    }
  }

  const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri
  const wsCfg = vscode.workspace.getConfiguration(undefined, wsFolder)
  for (const [family, config] of Object.entries(extensionSets)) {
    if (!profileManager.isActive(family)) continue
    const ds = Array.isArray(config) ? {} : config.disableSettings || {}
    const displayName = FAMILY_DISPLAY[family] || family
    for (const [key, disabledValue] of Object.entries(ds)) {
      const dedupeKey = `${key}@workspace`
      if (seen.has(dedupeKey)) continue
      const inspection = wsCfg.inspect(key)
      const actual = inspection?.workspaceFolderValue ?? inspection?.workspaceValue
      if (actual !== undefined && JSON.stringify(actual) === JSON.stringify(disabledValue)) {
        seen.add(dedupeKey)
        mismatches.push({
          key,
          expected: undefined,
          actual,
          family: displayName,
          scope: 'workspace'
        })
      }
    }
  }

  return mismatches
}

export async function writeMismatchSetting(
  key: string,
  value: unknown,
  scope: string
): Promise<void> {
  const target =
    scope === 'user' ? vscode.ConfigurationTarget.Global : vscode.ConfigurationTarget.Workspace
  const dot = key.lastIndexOf('.')
  if (dot > 0) {
    const section = key.substring(0, dot)
    const leaf = key.substring(dot + 1)
    try {
      await vscode.workspace.getConfiguration(section).update(leaf, value, target)
    } catch {
      const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri
      await vscode.workspace.getConfiguration(undefined, wsFolder).update(key, value, target)
    }
  } else {
    await vscode.workspace.getConfiguration().update(key, value, target)
  }
}

export async function handleMessage(
  msg: WebviewMessage,
  { refreshAll, showSectionLoading }: SectionContext
): Promise<boolean> {
  switch (msg.type) {
    case 'installExtension':
      log(`Search extension: ${msg.extensionId}`)
      await vscode.commands.executeCommand('workbench.extensions.search', msg.extensionId)
      return true
    case 'applySingleSetting': {
      showSectionLoading('ideHealth')
      try {
        await writeMismatchSetting(msg.key as string, msg.expected, msg.scope as string)
        notifyInfo(
          `CMK ▸ IDE: Applied ${msg.key}`,
          `${JSON.stringify(msg.expected)} [${msg.scope}]`
        )
      } catch (err) {
        notifyWarn(`CMK ▸ IDE: Failed to apply ${msg.key}`, (err as Error).message)
      }
      refreshAll()
      return true
    }
    case 'applyFamilyMismatches': {
      const family = msg.family as string
      const mismatches = getSettingsMismatches().filter((m) => m.family === family)
      if (mismatches.length === 0) {
        notifyInfo(`CMK ▸ IDE: All ${family} settings already match.`)
        return true
      }
      showSectionLoading('ideHealth')
      let applied = 0
      const failed: string[] = []
      for (const m of mismatches) {
        try {
          await writeMismatchSetting(m.key, m.expected, m.scope)
          applied++
        } catch {
          failed.push(m.key)
        }
      }
      if (failed.length > 0) {
        notifyWarn(
          `CMK ▸ IDE: Applied ${applied} ${family} settings, ${failed.length} failed`,
          failed.join(', ')
        )
      } else {
        notifyInfo(`CMK ▸ IDE: Applied ${applied} ${family} settings.`)
      }
      refreshAll()
      return true
    }
    case 'applyAllMismatches': {
      const mismatches = getSettingsMismatches()
      if (mismatches.length === 0) {
        notifyInfo('CMK ▸ IDE: All settings already match.')
        return true
      }
      showSectionLoading('ideHealth')
      let applied = 0
      const failed: string[] = []
      for (const m of mismatches) {
        try {
          await writeMismatchSetting(m.key, m.expected, m.scope)
          applied++
        } catch {
          failed.push(m.key)
        }
      }
      if (failed.length > 0) {
        notifyWarn(
          `CMK ▸ IDE: Applied ${applied} settings, ${failed.length} failed`,
          failed.join(', ')
        )
      } else {
        notifyInfo(`CMK ▸ IDE: Applied ${applied} settings.`)
      }
      refreshAll()
      return true
    }
    default:
      return false
  }
}

export function render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const { pythonEnvsActive, extensionHealth, settingsMismatches, versionMismatch } = state

  const installedVersion = vscode.extensions.getExtension('checkmk.cmk-vscode')?.packageJSON
    ?.version as string | undefined

  const versionHtml = installedVersion
    ? `<div class="env-row">
        <span class="env-label">Extension</span>
        <span class="env-value">v${esc(installedVersion)}</span>
      </div>`
    : ''

  const versionBanner = versionMismatch
    ? `<div class="banner">
        <span class="banner-icon">&#9888;</span>
        <span class="banner-text">Update available: <b>v${esc(versionMismatch.installed)}</b> → <b>v${esc(versionMismatch.workspace)}</b></span>
        <button class="btn btn-small" data-action="exec" data-id="cmk.rebuildExtension"><span class="codicon codicon-package"></span> Install</button>
      </div>`
    : ''

  const pyEnvsBanner = pythonEnvsActive
    ? `
    <div class="banner">
      <span class="banner-icon">&#9888;</span>
      <span class="banner-text"><b>Python Environments</b> (ms-python.vscode-python-envs) continuously scans for Python interpreters, causing high CPU and file I/O. It is not needed for Checkmk development.
        <br><button class="btn btn-small" data-action="exec" data-id="cmk.disableExtension">Show Extension</button>
      </span>
    </div>`
    : ''

  const truncate = (v: unknown, max = 60) => {
    const s = JSON.stringify(v)
    return s.length > max ? s.slice(0, max) + '…' : s
  }
  let settingsHtml: string
  if (settingsMismatches.length === 0) {
    settingsHtml = `<div class="build-row ok"><span class="card-icon">&#10003;</span><span class="build-name">All settings match</span></div>`
  } else {
    const applyBtn = `<div class="apply-wrapper"><button class="btn" data-action="apply-all-mismatches"><span class="codicon codicon-wrench"></span> Apply All (${settingsMismatches.length})</button></div>`
    const grouped = new Map<string, SettingsMismatch[]>()
    for (const m of settingsMismatches) {
      const key = m.family
      if (!grouped.has(key)) grouped.set(key, [])
      grouped.get(key)!.push(m)
    }
    const families = Array.from(grouped.entries())
      .map(([family, mismatches]) => {
        const rows = mismatches
          .map((m) => {
            const actualStr =
              m.actual === undefined
                ? '<i>not set</i>'
                : `<code title="${esc(JSON.stringify(m.actual))}">${esc(truncate(m.actual))}</code>`
            const expectedStr = `<code title="${esc(JSON.stringify(m.expected))}">${esc(truncate(m.expected))}</code>`
            const copyValue = esc(JSON.stringify({ [m.key]: m.expected }))
            const applyData = esc(
              JSON.stringify({ key: m.key, expected: m.expected, scope: m.scope })
            )
            return `<div class="setting-row">
          <div class="setting-header">
            <span class="setting-key">${m.key}</span>
            <button class="btn btn-small btn-icon btn-copy" data-action="apply-setting" data-setting="${applyData}" title="Apply setting"><span class="codicon codicon-wrench"></span></button>
            <button class="btn btn-small btn-icon btn-copy" data-action="copy-setting" data-value="${copyValue}" title="Copy setting"><span class="codicon codicon-copy"></span></button>
          </div>
          <div class="setting-diff">
            <div class="setting-line setting-expected">expected: ${expectedStr}</div>
            <div class="setting-line setting-actual">&#9888; current: ${actualStr}</div>
          </div>
          <div class="setting-footer">
            <span class="tag scope-${m.scope}">${m.scope}</span>
          </div>
        </div>`
          })
          .join('')
        const applyFamilyBtn = `<div class="apply-family-wrapper"><button class="btn btn-small" data-action="apply-family-mismatches" data-family="${esc(family)}"><span class="codicon codicon-wrench"></span> Apply ${family} (${mismatches.length})</button></div>`
        return `<div class="ext-family">
        <div class="ext-family-header stale" data-action="toggle-accordion">
          <span class="card-icon">&#9888;</span>
          <span class="ext-family-name">${family}</span>
          <span class="ext-count">${mismatches.length}</span>
          <span class="ext-chevron codicon codicon-chevron-right"></span>
        </div>
        <div class="ext-family-body">${applyFamilyBtn}${rows}</div>
      </div>`
      })
      .join('')
    settingsHtml = applyBtn + families
  }

  const extFamilies = extensionHealth
    .map((f) => {
      const icon = f.allInstalled ? '&#10003;' : '&#9888;'
      const cls = f.allInstalled ? 'ok' : 'stale'
      const badge = f.required ? '<span class="tag required">required</span>' : ''
      const extRows = f.extensions
        .map((e) => {
          const eIcon = e.installed ? '&#10003;' : '&#10007;'
          const eCls = e.installed ? 'ext-ok' : 'ext-missing'
          const installBtn = e.installed
            ? ''
            : `<button class="btn btn-small" data-action="install-ext" data-id="${e.id}"><span class="codicon codicon-package"></span> Install</button>`
          return `<div class="ext-row ${eCls}"><span class="ext-icon">${eIcon}</span><span class="ext-id">${e.id}</span>${installBtn}</div>`
        })
        .join('')
      return `<div class="ext-family">
      <div class="ext-family-header ${cls}" data-action="toggle-accordion">
        <span class="card-icon">${icon}</span>
        <span class="ext-family-name">${f.displayName}</span>
        ${badge}
        <span class="ext-count">${f.installedCount}/${f.extensions.length}</span>
        <span class="ext-chevron codicon codicon-chevron-right"></span>
      </div>
      <div class="ext-family-body">${extRows}</div>
    </div>`
    })
    .join('')

  return wrap(
    nonce,
    sectionCss,
    `${versionHtml}${versionBanner}${pyEnvsBanner}` +
      `<div class="section-label">Settings</div>${settingsHtml}` +
      `<div class="section-label">Extensions</div>${extFamilies}`,
    codiconUri,
    cspSource
  )
}
