/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { type ScopedSetting, writeSetting } from '../core/config'
import { FAMILY_DISPLAY, PROFILE_LABELS } from '../core/constants'
import { log, notifyInfo } from '../core/log'

const PRIORITIES: Record<string, number> = {
  python: 53,
  frontend: 52,
  rust: 51
}

const DEFAULT_ACTIVE = ['python', 'frontend']

export type ActivateFn = (context: vscode.ExtensionContext) => vscode.Disposable[] | void

export interface ProfileInfo {
  name: string
  active: boolean
  loading: boolean
  hasIssues: boolean
  label: string
  fullName: string
}

interface FamilyState {
  activate: ActivateFn | null
  disableSettings: ScopedSetting[]
  disposables: vscode.Disposable[]
  active: boolean
  hasIssues: boolean
  loading: boolean
  statusBarItem: vscode.StatusBarItem | null
}

const families: Record<string, FamilyState> = {
  python: {
    activate: null,
    disableSettings: [],
    disposables: [],
    active: false,
    hasIssues: false,
    loading: false,
    statusBarItem: null
  },
  frontend: {
    activate: null,
    disableSettings: [],
    disposables: [],
    active: false,
    hasIssues: false,
    loading: false,
    statusBarItem: null
  },
  rust: {
    activate: null,
    disableSettings: [],
    disposables: [],
    active: false,
    hasIssues: false,
    loading: false,
    statusBarItem: null
  }
}

let _context: vscode.ExtensionContext | null = null
let _onRefresh: (() => void) | null = null

export function setOnRefresh(fn: () => void): void {
  _onRefresh = fn
}

export function register(
  name: string,
  activateFn: ActivateFn,
  disableSettings?: ScopedSetting[]
): void {
  if (families[name]) {
    families[name].activate = activateFn
    families[name].disableSettings = disableSettings || []
  }
}

export async function start(name: string): Promise<void> {
  const family = families[name]
  if (!family || family.active || !family.activate || !_context) return
  log(`Enable profile: ${FAMILY_DISPLAY[name]}`)
  family.loading = true
  showLoading(name)
  try {
    family.disposables = family.activate(_context) || []
    family.active = true
    await saveActiveProfiles()
  } finally {
    family.loading = false
    updateStatusBarItem(name)
  }
  notifyInfo(`CMK: ${FAMILY_DISPLAY[name]} profile enabled`)
}

export async function stop(name: string): Promise<void> {
  const family = families[name]
  if (!family || !family.active) return
  log(`Disable profile: ${FAMILY_DISPLAY[name]}`)
  family.loading = true
  showLoading(name)
  try {
    for (const d of family.disposables) {
      try {
        d.dispose()
      } catch {
        /* already disposed */
      }
    }
    family.disposables = []
    family.active = false
    family.hasIssues = false
    await saveActiveProfiles()
  } finally {
    family.loading = false
    updateStatusBarItem(name)
  }
  notifyInfo(`CMK: ${FAMILY_DISPLAY[name]} profile disabled`)
}

export async function toggle(name: string): Promise<void> {
  if (families[name]?.loading) return
  if (families[name]?.active) {
    await stop(name)
  } else {
    await start(name)
  }
}

export function isActive(name: string): boolean {
  return families[name]?.active || false
}

export function getAll(): ProfileInfo[] {
  return Object.keys(families).map((name) => ({
    name,
    active: families[name].active,
    loading: families[name].loading,
    hasIssues: families[name].hasIssues,
    label: PROFILE_LABELS[name] || name,
    fullName: name.charAt(0).toUpperCase() + name.slice(1)
  }))
}

export function setLoading(name: string, loading: boolean): void {
  const family = families[name]
  if (!family) return
  family.loading = loading
  if (loading) showLoading(name)
  else updateStatusBarItem(name)
}

export function setIssues(name: string, hasIssues: boolean): void {
  const family = families[name]
  if (!family) return
  if (family.hasIssues === hasIssues) return
  family.hasIssues = hasIssues
  updateStatusBarItem(name)
}

function showLoading(name: string): void {
  const family = families[name]
  if (!family.statusBarItem) return
  const label = PROFILE_LABELS[name] || name
  family.statusBarItem.text = `$(sync~spin) ${label}`
  family.statusBarItem.tooltip = `CMK: ${FAMILY_DISPLAY[name]} profile switching…`
  family.statusBarItem.color = undefined
  family.statusBarItem.backgroundColor = undefined
}

function updateStatusBarItem(name: string): void {
  const family = families[name]
  if (!family.statusBarItem) return
  const label = PROFILE_LABELS[name] || name

  if (family.active && family.hasIssues) {
    family.statusBarItem.text = `$(warning) ${label}`
    family.statusBarItem.tooltip = `CMK: ${FAMILY_DISPLAY[name]} profile active — has stale build targets`
    family.statusBarItem.color = undefined
    family.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground')
  } else if (family.active) {
    family.statusBarItem.text = `$(check) ${label}`
    family.statusBarItem.tooltip = `CMK: ${FAMILY_DISPLAY[name]} profile active — click to disable`
    family.statusBarItem.color = new vscode.ThemeColor('terminal.ansiGreen')
    family.statusBarItem.backgroundColor = undefined
  } else {
    family.statusBarItem.text = `$(circle-outline) ${label}`
    family.statusBarItem.tooltip = `CMK: ${FAMILY_DISPLAY[name]} profile inactive — click to enable`
    family.statusBarItem.color = undefined
    family.statusBarItem.backgroundColor = undefined
  }
}

export function getActiveProfiles(): string[] {
  const config = vscode.workspace.getConfiguration('cmk')
  const inspection = config.inspect<string[]>('activeProfiles')
  return inspection?.workspaceValue ?? DEFAULT_ACTIVE
}

function saveActiveProfiles(): Thenable<void> {
  const active = Object.keys(families).filter((name) => families[name].active)
  const config = vscode.workspace.getConfiguration('cmk')
  return config.update('activeProfiles', active, vscode.ConfigurationTarget.Workspace)
}

function createProfileStatusBarItems(context: vscode.ExtensionContext): void {
  for (const name of Object.keys(families)) {
    const family = families[name]
    const item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      PRIORITIES[name] || 50
    )
    item.command = `cmk.toggleProfile.${name}`
    family.statusBarItem = item
    item.show()
    context.subscriptions.push(item)

    context.subscriptions.push(
      vscode.commands.registerCommand(`cmk.toggleProfile.${name}`, async () => {
        await toggle(name)
        _onRefresh?.()
      })
    )
  }
}

export function init(context: vscode.ExtensionContext): void {
  _context = context
  log('Profile manager init')

  createProfileStatusBarItems(context)

  const saved = getActiveProfiles()
  log(`Restore profiles: ${JSON.stringify(saved)}`)
  for (const name of Object.keys(families)) {
    if (saved.includes(name) && families[name].activate) {
      families[name].disposables = families[name].activate!(context) || []
      families[name].active = true
    }
    updateStatusBarItem(name)
  }

  applyInactiveDisableSettings()
}

async function applyInactiveDisableSettings(): Promise<void> {
  log('Apply inactive disable-settings')
  for (const name of Object.keys(families)) {
    if (families[name].active) continue
    for (const { key, value, target } of families[name].disableSettings) {
      try {
        await writeSetting(key, value, target)
      } catch (err) {
        log(`Disable-setting failed: ${name} ${key} — ${(err as Error).message}`)
      }
    }
  }
}
