/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

const _out = vscode.window.createOutputChannel('CMK')

type Level = 'INFO' | 'WARN' | 'ERROR'

function fmt(level: Level, msg: string): string {
  const now = new Date()
  const date = now.toISOString().slice(0, 10)
  const time = now.toISOString().slice(11, 19)
  return `[${date} - ${time}] ${level}: ${msg}`
}

export function log(msg: string): void {
  _out.appendLine(fmt('INFO', msg))
}

export function warn(msg: string): void {
  _out.appendLine(fmt('WARN', msg))
}

export function error(msg: string): void {
  _out.appendLine(fmt('ERROR', msg))
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
