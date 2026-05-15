/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

const _out = vscode.window.createOutputChannel('CMK')

type Level = 'INFO' | 'WARN' | 'ERROR'

export type ActivityCategory =
  | 'omd'
  | 'profile'
  | 'command'
  | 'benchmark'
  | 'gerrit'
  | 'mypy'
  | 'jemalloc'
  | 'general'

export interface ActivityEvent {
  ts: number
  level: Level
  message: string
  category: ActivityCategory
}

const ACTIVITY_CAP = 200
let _events: ActivityEvent[] = []
let _onActivity: (() => void) | null = null

/** Registered by the Activity sidebar section so it can refresh when new events land. */
export function setActivityRefreshCallback(cb: (() => void) | null): void {
  _onActivity = cb
}

/** Most-recent-last list of the last ACTIVITY_CAP events (since extension activation). */
export function getActivityEvents(): ActivityEvent[] {
  return _events.slice()
}

/** Drop the buffered events. Output channel is unaffected. */
export function clearActivityEvents(): void {
  _events = []
  _onActivity?.()
}

function categorize(message: string): ActivityCategory {
  if (/^\[benchmark\]/.test(message)) return 'benchmark'
  if (/^(OMD |Create OMD site|omd-|Install cmk-dev-site|OMD ▸)/i.test(message)) return 'omd'
  if (/^(Enable|Disable) profile:/.test(message)) return 'profile'
  if (/^Execute command:/.test(message)) return 'command'
  if (/^(Gerrit|Push to Gerrit)/i.test(message)) return 'gerrit'
  if (/^(Mypy|cmk\.mypy|mypy:)/i.test(message)) return 'mypy'
  if (/jemalloc/i.test(message)) return 'jemalloc'
  return 'general'
}

function record(level: Level, message: string): void {
  _events.push({ ts: Date.now(), level, message, category: categorize(message) })
  if (_events.length > ACTIVITY_CAP) _events.splice(0, _events.length - ACTIVITY_CAP)
  _onActivity?.()
}

function fmt(level: Level, msg: string): string {
  const now = new Date()
  const date = now.toISOString().slice(0, 10)
  const time = now.toISOString().slice(11, 19)
  return `[${date} - ${time}] ${level}: ${msg}`
}

export function log(msg: string): void {
  _out.appendLine(fmt('INFO', msg))
  record('INFO', msg)
}

export function warn(msg: string): void {
  _out.appendLine(fmt('WARN', msg))
  record('WARN', msg)
}

export function error(msg: string): void {
  _out.appendLine(fmt('ERROR', msg))
  record('ERROR', msg)
}

/** Open the CMK Output channel in the bottom panel. */
export function showOutputChannel(): void {
  _out.show(true)
}

/**
 * Show info notification and log it.
 * @param detail — extra context logged to the output channel and shown as notification detail on expand.
 */
export function notifyInfo(
  msg: string,
  detail?: string,
  ...items: string[]
): Thenable<string | undefined> {
  log(detail ? `${msg} — ${detail}` : msg)
  return detail
    ? vscode.window.showInformationMessage(msg, { detail }, ...items)
    : vscode.window.showInformationMessage(msg, ...items)
}

/**
 * Show warning notification and log it.
 * @param detail — extra context logged to the output channel and shown as notification detail on expand.
 */
export function notifyWarn(
  msg: string,
  detail?: string,
  ...items: string[]
): Thenable<string | undefined> {
  warn(detail ? `${msg} — ${detail}` : msg)
  return detail
    ? vscode.window.showWarningMessage(msg, { detail }, ...items)
    : vscode.window.showWarningMessage(msg, ...items)
}

/**
 * Show error notification and log it.
 * @param detail — extra context logged to the output channel and shown as notification detail on expand.
 */
export function notifyError(
  msg: string,
  detail?: string,
  ...items: string[]
): Thenable<string | undefined> {
  error(detail ? `${msg} — ${detail}` : msg)
  return detail
    ? vscode.window.showErrorMessage(msg, { detail }, ...items)
    : vscode.window.showErrorMessage(msg, ...items)
}

/** Catch unhandled JS errors and rejections and log them. */
export function registerErrorHandlers(): void {
  process.on('uncaughtException', (err) => {
    error(`Uncaught exception: ${err.stack || err.message}`)
  })
  process.on('unhandledRejection', (reason) => {
    const msg = reason instanceof Error ? reason.stack || reason.message : String(reason)
    error(`Unhandled rejection: ${msg}`)
  })
}
