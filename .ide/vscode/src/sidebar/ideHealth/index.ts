/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { type SettingsEntry, buildEffectiveSettings } from '../../build/settings'
import { type ExtensionSets, loadConfig, resolveVariables } from '../../core/config'
import { FAMILY_DISPLAY } from '../../core/constants'
import { log, notifyInfo, notifyWarn } from '../../core/log'
import * as profileManager from '../../profiles/profileManager'
import {
  activateTarget,
  addTargetToBaseline,
  deactivateTarget,
  removeTargetFromBaseline
} from '../../profiles/python/dynamicMypyTargets'
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

/**
 * Read `.vscode/settings.json` once and return the parsed top-level keys.
 * VS Code's `inspect()` returns undefined for keys whose owning extension
 * isn't installed, so we consult the file itself as the source of truth.
 */
function readFolderSettingsFile(wsFolder: vscode.Uri | undefined): Record<string, unknown> {
  if (!wsFolder) return {}
  const settingsPath = path.join(wsFolder.fsPath, '.vscode', 'settings.json')
  try {
    const raw = fs.readFileSync(settingsPath, 'utf-8')
    if (raw.trim() === '') return {}
    return JSON.parse(raw) as Record<string, unknown>
  } catch {
    return {}
  }
}

export function getSettingsMismatches(
  settingsConfig?: Record<string, SettingsEntry> | null
): SettingsMismatch[] {
  const settingsSets: Record<string, SettingsEntry> =
    settingsConfig || loadConfig<Record<string, SettingsEntry>>('settings')
  const mismatches: SettingsMismatch[] = []

  const isFolderWorkspace = vscode.workspace.workspaceFile === undefined
  const folderFileSettings = readFolderSettingsFile(vscode.workspace.workspaceFolders?.[0]?.uri)

  type Inspection = ReturnType<vscode.WorkspaceConfiguration['inspect']>
  const SCOPE_CONFIG = [
    {
      scope: 'folder' as const,
      label: 'folder',
      getter: (i: Inspection, key: string) => i?.workspaceFolderValue ?? folderFileSettings[key]
    },
    {
      scope: 'workspace' as const,
      label: 'workspace',
      getter: (i: Inspection, key: string) =>
        i?.workspaceValue ??
        (isFolderWorkspace ? (i?.workspaceFolderValue ?? folderFileSettings[key]) : undefined)
    },
    {
      scope: 'user' as const,
      label: 'user',
      getter: (i: Inspection) => i?.globalValue
    }
  ]

  const seen = new Set<string>()

  for (const [family, settingsEntry] of Object.entries(settingsSets)) {
    const displayName = FAMILY_DISPLAY[family] || family
    const { folderSettings, workspaceSettings, userSettings } = buildEffectiveSettings(
      settingsEntry,
      family
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
        const actual = getter(inspection, key)

        if (actual === undefined) {
          mismatches.push({ key, expected, actual: undefined, family: displayName, scope: label })
        } else if (JSON.stringify(actual) !== JSON.stringify(expected)) {
          mismatches.push({ key, expected, actual, family: displayName, scope: label })
        }
      }
    }
  }

  const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri
  for (const [family, settingsEntry] of Object.entries(settingsSets)) {
    if (!profileManager.isActive(family)) continue
    const displayName = FAMILY_DISPLAY[family] || family
    const disableScopes = [
      {
        settings: settingsEntry.disableFolder || {},
        label: 'folder',
        getter: (i: Inspection) => i?.workspaceFolderValue
      },
      {
        settings: settingsEntry.disableWorkspace || {},
        label: 'workspace',
        getter: (i: Inspection) =>
          i?.workspaceValue ?? (isFolderWorkspace ? i?.workspaceFolderValue : undefined)
      },
      {
        settings: settingsEntry.disableUser || {},
        label: 'user',
        getter: (i: Inspection) => i?.globalValue
      }
    ]
    for (const { settings: ds, label, getter } of disableScopes) {
      if (!ds || Object.keys(ds).length === 0) continue
      const resource = label === 'folder' ? wsFolder : undefined
      const cfg = vscode.workspace.getConfiguration(undefined, resource)
      for (const [key, disabledValue] of Object.entries(ds)) {
        const dedupeKey = `${key}@${label}`
        if (seen.has(dedupeKey)) continue
        const inspection = cfg.inspect(key)
        const actual = getter(inspection)
        if (actual !== undefined && JSON.stringify(actual) === JSON.stringify(disabledValue)) {
          seen.add(dedupeKey)
          mismatches.push({
            key,
            expected: undefined,
            actual,
            family: displayName,
            scope: label
          })
        }
      }
    }
  }

  return mismatches
}

/**
 * Write all folder-scoped mismatches in a single JSON merge-and-write to
 * `.vscode/settings.json`. Returns the keys that were NOT batched (e.g. file
 * is JSONC with comments and couldn't be parsed) so the caller can fall back
 * to the per-key API for those.
 */
async function writeFolderBatch(
  wsFolder: vscode.Uri,
  entries: Array<{ key: string; value: unknown }>
): Promise<{ batched: number; unbatched: Array<{ key: string; value: unknown }> }> {
  if (entries.length === 0) return { batched: 0, unbatched: [] }
  const settingsPath = path.join(wsFolder.fsPath, '.vscode', 'settings.json')
  let raw = '{}'
  try {
    raw = fs.readFileSync(settingsPath, 'utf-8')
    if (raw.trim() === '') raw = '{}'
  } catch {
    /* file doesn't exist yet */
  }
  let parsed: Record<string, unknown>
  try {
    parsed = JSON.parse(raw) as Record<string, unknown>
  } catch {
    // JSONC with comments/trailing commas — caller falls back per key
    return { batched: 0, unbatched: entries }
  }
  for (const { key, value } of entries) {
    if (value === undefined) delete parsed[key]
    else parsed[key] = value
  }
  fs.mkdirSync(path.dirname(settingsPath), { recursive: true })
  fs.writeFileSync(settingsPath, JSON.stringify(parsed, null, 2) + '\n')
  return { batched: entries.length, unbatched: [] }
}

/**
 * Apply many mismatches efficiently. Folder-scoped writes are coalesced into
 * a single file write (avoiding per-key format-on-save cascades when the
 * settings file is open in an editor); other scopes go through the API.
 */
export async function writeMismatchSettingsBatch(
  mismatches: Array<{ key: string; expected: unknown; scope: string }>
): Promise<{ applied: number; failed: string[] }> {
  const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri
  const folderEntries: Array<{ key: string; value: unknown }> = []
  const others: typeof mismatches = []
  for (const m of mismatches) {
    if (m.scope === 'folder' && wsFolder) {
      folderEntries.push({ key: m.key, value: m.expected })
    } else {
      others.push(m)
    }
  }

  let applied = 0
  const failed: string[] = []

  if (wsFolder && folderEntries.length > 0) {
    try {
      const { batched, unbatched } = await writeFolderBatch(wsFolder, folderEntries)
      applied += batched
      for (const { key, value } of unbatched) others.push({ key, expected: value, scope: 'folder' })
    } catch {
      for (const e of folderEntries) others.push({ key: e.key, expected: e.value, scope: 'folder' })
    }
  }

  for (const m of others) {
    try {
      await writeMismatchSetting(m.key, m.expected, m.scope)
      applied++
    } catch {
      failed.push(m.key)
    }
  }

  return { applied, failed }
}

export async function writeMismatchSetting(
  key: string,
  value: unknown,
  scope: string
): Promise<void> {
  const target =
    scope === 'user'
      ? vscode.ConfigurationTarget.Global
      : scope === 'folder'
        ? vscode.ConfigurationTarget.WorkspaceFolder
        : vscode.ConfigurationTarget.Workspace
  const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri
  // For folder scope, write directly to .vscode/settings.json. The VS Code
  // API rejects updates for keys whose owning extension isn't loaded
  // (e.g. djlint.useVenv when monosans.djlint isn't installed yet).
  if (scope === 'folder' && wsFolder) {
    const { unbatched } = await writeFolderBatch(wsFolder, [{ key, value }])
    if (unbatched.length === 0) return
  }
  const resource = target === vscode.ConfigurationTarget.WorkspaceFolder ? wsFolder : undefined
  const dot = key.lastIndexOf('.')
  if (dot > 0) {
    const section = key.substring(0, dot)
    const leaf = key.substring(dot + 1)
    try {
      await vscode.workspace.getConfiguration(section, resource).update(leaf, value, target)
    } catch {
      await vscode.workspace.getConfiguration(undefined, resource).update(key, value, target)
    }
  } else {
    await vscode.workspace.getConfiguration(undefined, resource).update(key, value, target)
  }
}

export async function handleMessage(
  msg: WebviewMessage,
  { refreshAll }: SectionContext
): Promise<boolean> {
  switch (msg.type) {
    case 'installExtension':
      log(`Search extension: ${msg.extensionId}`)
      await vscode.commands.executeCommand('workbench.extensions.search', msg.extensionId)
      return true
    case 'applySingleSetting': {
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
      const { applied, failed } = await writeMismatchSettingsBatch(mismatches)
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
      const { applied, failed } = await writeMismatchSettingsBatch(mismatches)
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
    case 'mypyAddBaseline': {
      const target = msg.target as string
      if (target) {
        addTargetToBaseline(target)
        refreshAll()
      }
      return true
    }
    case 'mypyRemoveBaseline': {
      const target = msg.target as string
      if (target) {
        removeTargetFromBaseline(target)
        refreshAll()
      }
      return true
    }
    case 'mypyActivateTarget': {
      const target = msg.target as string
      if (target) {
        activateTarget(target)
        refreshAll()
      }
      return true
    }
    case 'mypyDeactivateTarget': {
      const target = msg.target as string
      if (target) {
        deactivateTarget(target)
        refreshAll()
      }
      return true
    }
    default:
      return false
  }
}

export function render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const {
    pythonEnvsActive,
    extensionHealth,
    settingsMismatches,
    versionMismatch,
    configInWorkspace,
    mypyTargets
  } = state

  const installedVersion = vscode.extensions.getExtension('checkmk.cmk-vscode')?.packageJSON
    ?.version as string | undefined

  const versionHtml = installedVersion
    ? `<div class="env-row">
        <span class="env-label">Extension</span>
        <span class="env-value">v${esc(installedVersion)}</span>
        <button class="btn btn-small btn-icon" data-action="exec" data-id="cmk.pickChangelog" title="Browse changelog">
          <span class="codicon codicon-history"></span>
        </button>
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

  const noConfigBanner = !configInWorkspace
    ? `<div class="banner">
        <span class="banner-icon">&#9888;</span>
        <span class="banner-text">No configuration recommendations found. Please evaluate extensions and settings independently.</span>
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
            const expectedStr =
              m.expected === undefined
                ? '<i>remove</i>'
                : `<code title="${esc(JSON.stringify(m.expected))}">${esc(truncate(m.expected))}</code>`
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

  const mypyHtml = renderMypyTargets(mypyTargets)

  return wrap(
    nonce,
    sectionCss,
    `${versionHtml}${versionBanner}${pyEnvsBanner}${noConfigBanner}` +
      `${mypyHtml}` +
      `<div class="section-label">Settings</div>${settingsHtml}` +
      `<div class="section-label">Extensions</div>${extFamilies}`,
    codiconUri,
    cspSource
  )
}

function renderMypyTargets(info: StateCache['mypyTargets']): string {
  if (!info.pythonProfileActive) return ''
  const {
    enabled,
    activeCount,
    catalogSize,
    activeTargets,
    baselineTargets,
    alwaysOnTargets,
    stagedActiveAdd,
    stagedActiveRemove,
    stagedBaselineAdd,
    stagedBaselineRemove,
    catalog
  } = info

  const statusCls = enabled ? 'ok' : 'stale'
  const statusIcon = enabled ? '&#10003;' : '&#9888;'
  const statusText = enabled
    ? `${activeCount} active / ${catalogSize} available`
    : `disabled — checking full catalog (${catalogSize})`

  const actions = enabled
    ? `<button class="btn btn-small btn-icon" data-action="exec" data-id="cmk.mypy.resetTargetsToBaseline" title="Apply baseline">
        <span class="codicon codicon-refresh"></span>
      </button>
      <button class="btn btn-small btn-icon" data-action="exec" data-id="cmk.mypy.activateTargetPick" title="Activate target(s)…">
        <span class="codicon codicon-new-collection"></span>
      </button>`
    : ''

  const activeSet = new Set(activeTargets)
  const baselineSet = new Set(baselineTargets)
  const alwaysOnSet = new Set(alwaysOnTargets)
  const stagedActiveAddSet = new Set(stagedActiveAdd)
  const stagedActiveRemoveSet = new Set(stagedActiveRemove)
  const stagedBaselineAddSet = new Set(stagedBaselineAdd)
  const stagedBaselineRemoveSet = new Set(stagedBaselineRemove)
  const stagedAll = new Set<string>([
    ...stagedActiveAdd,
    ...stagedActiveRemove,
    ...stagedBaselineAdd,
    ...stagedBaselineRemove
  ])

  const targetRow = (t: string): string => {
    const isAlwaysOn = alwaysOnSet.has(t)
    const isAppliedActive = activeSet.has(t) || isAlwaysOn
    const effectiveActive =
      (isAppliedActive && !stagedActiveRemoveSet.has(t)) || stagedActiveAddSet.has(t)
    const appliedBaseline = baselineSet.has(t) || isAlwaysOn
    const effectiveBaseline =
      (appliedBaseline && !stagedBaselineRemoveSet.has(t)) || stagedBaselineAddSet.has(t)
    const isStaged = stagedAll.has(t)

    const statusSymbol = effectiveActive
      ? `<span class="mypy-target-status ok" title="Active">&#10003;</span>`
      : `<span class="mypy-target-status missing" title="Inactive">&#10007;</span>`

    const labels: string[] = []
    if (isAlwaysOn) labels.push(`<span class="tag mypy-alwayson-tag">always on</span>`)
    else if (effectiveBaseline)
      labels.push(`<span class="tag mypy-baseline-tag">user baseline</span>`)
    if (isStaged) labels.push(`<span class="tag mypy-staged-tag">staged</span>`)

    const buttons: string[] = []
    if (!effectiveActive) {
      buttons.push(
        `<button class="btn btn-small btn-icon" data-action="mypy-activate-target" data-target="${esc(t)}" title="Stage activate">
          <span class="codicon codicon-add"></span>
        </button>`
      )
    } else if (!isAlwaysOn) {
      buttons.push(
        `<button class="btn btn-small btn-icon" data-action="mypy-deactivate-target" data-target="${esc(t)}" title="Stage deactivate">
          <span class="codicon codicon-remove"></span>
        </button>`
      )
    }
    if (!isAlwaysOn) {
      const pinAction = effectiveBaseline ? 'mypy-remove-baseline' : 'mypy-add-baseline'
      const pinIcon = effectiveBaseline ? 'codicon-pinned' : 'codicon-pin'
      const pinTitle = effectiveBaseline ? 'Stage: remove from baseline' : 'Stage: add to baseline'
      buttons.push(
        `<button class="btn btn-small btn-icon" data-action="${pinAction}" data-target="${esc(t)}" title="${pinTitle}">
          <span class="codicon ${pinIcon}"></span>
        </button>`
      )
    }

    return `<div class="mypy-target ${effectiveActive ? 'mypy-target-active' : 'mypy-target-inactive'}">
      ${statusSymbol}
      <span class="mypy-target-name">${esc(t)}</span>
      ${labels.join('')}
      ${buttons.join('')}
    </div>`
  }

  const rank = (t: string): number => {
    if (alwaysOnSet.has(t)) return 0
    const appliedBaseline = baselineSet.has(t)
    const effectiveBaseline =
      (appliedBaseline && !stagedBaselineRemoveSet.has(t)) || stagedBaselineAddSet.has(t)
    if (effectiveBaseline) return 1
    const isAppliedActive = activeSet.has(t)
    const effectiveActive =
      (isAppliedActive && !stagedActiveRemoveSet.has(t)) || stagedActiveAddSet.has(t)
    if (effectiveActive) return 2
    return 3
  }
  const sortedCatalog = [...catalog].sort((a, b) => {
    const diff = rank(a) - rank(b)
    return diff !== 0 ? diff : a.localeCompare(b)
  })

  const body = enabled
    ? sortedCatalog.length > 0
      ? `<div class="mypy-targets-list">${sortedCatalog.map(targetRow).join('')}</div>`
      : `<div class="mypy-empty"><i>No targets discovered in the workspace.</i></div>`
    : `<div class="mypy-empty"><i>Enable <code>cmk.mypy.dynamicTargets.enabled</code> to start dmypy with a minimal target set that grows on demand.</i></div>`

  const stagedBanner =
    enabled && stagedAll.size > 0
      ? `<div class="banner mypy-staged-banner">
          <span class="banner-icon">&#9888;</span>
          <span class="banner-text"><b>${stagedAll.size} staged change(s)</b>: ${[...stagedAll]
            .sort()
            .map((t) => `<code>${esc(t)}</code>`)
            .join(', ')}</span>
          <button class="btn btn-small" data-action="exec" data-id="cmk.mypy.applyStagedTargets" title="Apply staged changes (restarts dmypy)"><span class="codicon codicon-check"></span> Apply</button>
          <button class="btn btn-small" data-action="exec" data-id="cmk.mypy.discardStagedTargets" title="Discard staged changes"><span class="codicon codicon-close"></span> Discard</button>
        </div>`
      : ''

  return `<div class="section-label">Mypy Targets</div>
    ${stagedBanner}
    <div class="ext-family mypy-targets-family">
      <div class="ext-family-header ${statusCls}" data-action="toggle-accordion">
        <span class="card-icon">${statusIcon}</span>
        <span class="ext-family-name">Dynamic targets</span>
        <span class="ext-count">${esc(statusText)}</span>
        ${actions}
        <span class="ext-chevron codicon codicon-chevron-right"></span>
      </div>
      <div class="ext-family-body">${body}</div>
    </div>`
}
