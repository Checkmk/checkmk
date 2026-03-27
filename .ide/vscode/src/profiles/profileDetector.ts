/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as path from 'path'
import * as vscode from 'vscode'

import { log } from '../core/log'
import * as profileManager from './profileManager'

// ── Profile-to-language mapping ──

const PROFILE_LANGUAGES: Record<string, Set<string>> = {
  python: new Set(['python']),
  frontend: new Set([
    'vue',
    'typescript',
    'javascript',
    'typescriptreact',
    'javascriptreact',
    'css',
    'scss',
    'html'
  ]),
  rust: new Set(['rust'])
}

const PROFILE_EXTENSIONS: Record<string, Set<string>> = {
  python: new Set(['.py', '.pyi']),
  frontend: new Set(['.vue', '.ts', '.js', '.tsx', '.jsx', '.css', '.scss']),
  rust: new Set(['.rs'])
}

const PROFILE_DISPLAY: Record<string, string> = {
  python: 'Python',
  frontend: 'UI',
  rust: 'Rust'
}

// ── Thresholds ──

const COOLDOWN_MS = 15 * 60 * 1000
const SNOOZE_MS = 60 * 60 * 1000
const ENABLE_OPEN_THRESHOLD = 2
const INACTIVITY_CHECK_INTERVAL_MS = 5 * 60 * 1000
const SUPPRESSED_KEY = 'cmk.profileDetector.suppressed'

// ── State ──

interface ActivityState {
  lastSeen: number
  lastEdited: number
  openCount: number
}

const _activity: Record<string, ActivityState> = {}
const _cooldowns: Record<string, number> = {}
const _snoozed: Record<string, number> = {}
let _suppressed: string[] = []
let _context: vscode.ExtensionContext | null = null

function initActivity(): void {
  for (const name of Object.keys(PROFILE_LANGUAGES)) {
    _activity[name] = { lastSeen: 0, lastEdited: 0, openCount: 0 }
  }
}

// ── Classification ──

function classifyDocument(doc: vscode.TextDocument | undefined): string | null {
  if (!doc) return null
  const langId = doc.languageId
  const ext = path.extname(doc.fileName).toLowerCase()

  for (const [profile, langs] of Object.entries(PROFILE_LANGUAGES)) {
    if (langs.has(langId)) return profile
  }
  for (const [profile, exts] of Object.entries(PROFILE_EXTENSIONS)) {
    if (exts.has(ext)) return profile
  }
  return null
}

// ── Suggestion guards ──

function isEnabled(): boolean {
  return vscode.workspace.getConfiguration('cmk').get('profileDetector.enabled', true)
}

function getInactivityMinutes(): number {
  return vscode.workspace.getConfiguration('cmk').get('profileDetector.inactivityMinutes', 30)
}

function canSuggest(profile: string): boolean {
  if (!isEnabled()) return false
  if (_suppressed.includes(profile)) return false
  if (_snoozed[profile] && Date.now() < _snoozed[profile]) return false
  if (_cooldowns[profile] && Date.now() - _cooldowns[profile] < COOLDOWN_MS) return false
  const all = profileManager.getAll()
  const info = all.find((p) => p.name === profile)
  if (info?.loading) return false
  return true
}

function markSuggested(profile: string): void {
  _cooldowns[profile] = Date.now()
}

// ── Suggestions ──

function suggestEnable(profile: string): void {
  if (!canSuggest(profile)) return
  markSuggested(profile)

  const name = PROFILE_DISPLAY[profile]
  log(`Suggest enable profile: ${name}`)
  vscode.window
    .showInformationMessage(
      `CMK: You're working with ${name} files but the ${name} profile is disabled. Enable it for full IDE support?`,
      'Enable',
      'Snooze (1h)',
      `Don't Ask for ${name}`
    )
    .then((choice) => {
      if (choice === 'Enable') {
        profileManager.start(profile)
        _activity[profile].lastSeen = Date.now()
        _activity[profile].lastEdited = Date.now()
      } else if (choice === 'Snooze (1h)') {
        _snoozed[profile] = Date.now() + SNOOZE_MS
      } else if (choice === `Don't Ask for ${name}`) {
        suppress(profile)
      }
    })
}

function suggestDisable(profile: string): void {
  if (!canSuggest(profile)) return
  markSuggested(profile)

  const name = PROFILE_DISPLAY[profile]
  const mins = getInactivityMinutes()
  log(`Suggest disable profile: ${name}`)
  vscode.window
    .showInformationMessage(
      `CMK: ${name} profile is active but no ${name} files opened in ${mins} min. Disable to save resources?`,
      'Disable',
      'Snooze (1h)',
      `Don't Ask for ${name}`
    )
    .then((choice) => {
      if (choice === 'Disable') {
        profileManager.stop(profile)
      } else if (choice === 'Snooze (1h)') {
        _snoozed[profile] = Date.now() + SNOOZE_MS
      } else if (choice === `Don't Ask for ${name}`) {
        suppress(profile)
      }
    })
}

function suppress(profile: string): void {
  if (!_suppressed.includes(profile)) {
    _suppressed.push(profile)
    _context?.globalState.update(SUPPRESSED_KEY, _suppressed)
  }
}

// ── Event handlers ──

function onEditorChange(editor: vscode.TextEditor | undefined): void {
  if (!editor || !isEnabled()) return
  const profile = classifyDocument(editor.document)
  if (!profile) return

  _activity[profile].lastSeen = Date.now()
  _activity[profile].openCount++

  if (!profileManager.isActive(profile) && _activity[profile].openCount >= ENABLE_OPEN_THRESHOLD) {
    suggestEnable(profile)
  }
}

function onDocumentEdit(event: vscode.TextDocumentChangeEvent): void {
  if (!isEnabled()) return
  const profile = classifyDocument(event.document)
  if (!profile) return

  _activity[profile].lastSeen = Date.now()
  _activity[profile].lastEdited = Date.now()

  if (!profileManager.isActive(profile)) {
    suggestEnable(profile)
  }
}

function checkDisableSuggestions(): void {
  if (!isEnabled()) return

  const inactivityMs = getInactivityMinutes() * 60 * 1000
  const now = Date.now()

  for (const profile of Object.keys(PROFILE_LANGUAGES)) {
    if (!profileManager.isActive(profile)) continue
    const activity = _activity[profile]
    if (activity.lastSeen === 0) continue
    if (now - activity.lastSeen >= inactivityMs) {
      suggestDisable(profile)
    }
  }
}

// ── Seeding ──

function seedFromVisibleEditors(): void {
  const now = Date.now()
  for (const editor of vscode.window.visibleTextEditors) {
    const profile = classifyDocument(editor.document)
    if (profile) {
      _activity[profile].lastSeen = now
      _activity[profile].openCount++
    }
  }
}

// ── Registration ──

export function registerProfileDetector(context: vscode.ExtensionContext): void {
  _context = context
  _suppressed = context.globalState.get<string[]>(SUPPRESSED_KEY, []) ?? []

  initActivity()
  seedFromVisibleEditors()

  context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(onEditorChange))

  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(onDocumentEdit))

  const timer = setInterval(checkDisableSuggestions, INACTIVITY_CHECK_INTERVAL_MS)
  context.subscriptions.push({ dispose: () => clearInterval(timer) })
}
