/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { shellExec } from './shell'

// ── Config types ──

export interface CommandConfig {
  name: string
  command: string
  requires?: string
  postAction?: string
}

export interface ExtensionFamilyConfig {
  extensions: string[]
  required?: boolean
  disableSettings?: Record<string, unknown>
  defaultPicked?: boolean
}

export type ExtensionEntry = string[] | ExtensionFamilyConfig
export type ExtensionSets = Record<string, ExtensionEntry>

export type SettingValue =
  | string
  | number
  | boolean
  | null
  | SettingValue[]
  | { [key: string]: SettingValue }

export interface SettingsScopeEntry {
  folderSettings?: Record<string, SettingValue>
  workspaceSettings?: Record<string, SettingValue>
  userSettings?: Record<string, SettingValue>
}

export type SettingsSets = Record<string, SettingsScopeEntry>

// ── Functions ──

export async function writeSetting(key: string, value: unknown): Promise<void> {
  const dot = key.lastIndexOf('.')
  if (dot > 0) {
    const section = key.substring(0, dot)
    const leaf = key.substring(dot + 1)
    await vscode.workspace
      .getConfiguration(section)
      .update(leaf, value, vscode.ConfigurationTarget.Workspace)
  } else {
    await vscode.workspace
      .getConfiguration()
      .update(key, value, vscode.ConfigurationTarget.Workspace)
  }
}

export function shellEscape(s: string): string {
  return "'" + String(s).replace(/'/g, "'\\''") + "'"
}

export function loadConfig<T = unknown>(name: string): T {
  // Prefer workspace config (branch-aware, always fresh)
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (wsPath) {
    const wsConfig = path.join(wsPath, '.ide', 'vscode', 'config', `${name}.json`)
    if (fs.existsSync(wsConfig)) {
      return JSON.parse(fs.readFileSync(wsConfig, 'utf8'))
    }
  }
  // Fallback to bundled config in installed VSIX
  return JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config', `${name}.json`), 'utf8'))
}

export function resolveVariables(value: SettingValue): SettingValue {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return value
  if (typeof value === 'string') {
    return value
      .replace(/\$\{workspaceFolder\}/g, wsPath)
      .replace(/\$\{HOME\}/g, os.homedir())
      .replace(/\$\{which:([^}]+)\}/g, (_m, bin) => shellExec(`which ${bin}`))
  }
  if (Array.isArray(value)) {
    return value.map((v) => resolveVariables(v))
  }
  if (typeof value === 'object' && value !== null) {
    const resolved: Record<string, SettingValue> = {}
    for (const [k, v] of Object.entries(value)) {
      resolved[k] = resolveVariables(v)
    }
    return resolved
  }
  return value
}

export function getExtensionIds(extensionSets: ExtensionSets, name: string): string[] {
  const entry = extensionSets[name]
  return Array.isArray(entry) ? entry : entry?.extensions || []
}

export function isRequired(extensionSets: ExtensionSets, name: string): boolean {
  const entry = extensionSets[name]
  return !Array.isArray(entry) && entry?.required === true
}

export function getRequiredFamilies(extensionSets: ExtensionSets): string[] {
  return Object.keys(extensionSets).filter((name) => isRequired(extensionSets, name))
}

export function getOptionalFamilies(extensionSets: ExtensionSets): string[] {
  return Object.keys(extensionSets).filter((name) => !isRequired(extensionSets, name))
}

export function isDefaultPicked(extensionSets: ExtensionSets, name: string): boolean {
  const entry = extensionSets[name]
  if (Array.isArray(entry)) return true
  return entry?.defaultPicked !== false
}

export function getDisableSettings(
  extensionSets: ExtensionSets,
  name: string
): Record<string, unknown> {
  const entry = extensionSets[name]
  if (Array.isArray(entry)) return {}
  return entry?.disableSettings || {}
}
