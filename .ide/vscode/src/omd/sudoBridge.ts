/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 *
 * Sudo bridge — reuses the `cmk.omdAuth` keepalive terminal's authenticated
 * sudo session for subsequent OMD queries. Avoids re-prompting the user for
 * every sudo-requiring operation when `tty_tickets` is enforced.
 *
 * Mechanism:
 * 1. `cmk.omdAuth` is redesigned so its shell returns to an interactive prompt
 *    after auth (keepalive runs as a backgrounded subshell).
 * 2. We send commands via `Terminal.sendText()`. The shell reads them as if
 *    typed by the user — no new TTY, no new sudo prompt.
 * 3. Output can't be captured directly from a VS Code terminal, so each
 *    command writes stdout/stderr + exit code to sentinel files in
 *    `/tmp/cmk-omd-bridge/`. We poll for `<id>.done` and read the files.
 */
import * as crypto from 'crypto'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { log } from '../core/log'

export const BRIDGE_DIR = path.join(os.tmpdir(), 'cmk-omd-bridge')
export const KEEPALIVE_READY = path.join(BRIDGE_DIR, 'keepalive.ready')

let _keepaliveTerm: vscode.Terminal | null = null

export function setKeepaliveTerminal(term: vscode.Terminal | null): void {
  _keepaliveTerm = term
}

export function getKeepaliveTerminal(): vscode.Terminal | null {
  return _keepaliveTerm
}

export function hasKeepalive(): boolean {
  return _keepaliveTerm !== null && fs.existsSync(KEEPALIVE_READY)
}

/**
 * Send `inner` (executed as `sudo sh -c "…"`) to the keepalive terminal.
 * Waits for completion via a sentinel file; returns captured output + rc.
 * Returns null if there's no keepalive or the command times out.
 */
export async function runInKeepaliveTerminal(
  inner: string,
  timeoutMs = 30_000
): Promise<{ output: string; exitCode: number } | null> {
  const term = _keepaliveTerm
  if (!term) return null
  if (!fs.existsSync(KEEPALIVE_READY)) return null

  try {
    fs.mkdirSync(BRIDGE_DIR, { recursive: true })
  } catch {
    /* ignore */
  }
  const id = crypto.randomUUID()
  const outPath = path.join(BRIDGE_DIR, `${id}.out`)
  const rcPath = path.join(BRIDGE_DIR, `${id}.rc`)
  const donePath = path.join(BRIDGE_DIR, `${id}.done`)

  // Escape for inclusion inside `sudo sh -c "…"`
  const escaped = inner.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\$/g, '\\$')
  const wrapped =
    `sudo sh -c "{ ${escaped}; } > ${outPath} 2>&1; ` +
    `echo \\$? > ${rcPath}; chmod 644 ${outPath} ${rcPath}; touch ${donePath}"`
  term.sendText(wrapped)

  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (fs.existsSync(donePath)) {
      let output = ''
      let exitCode: number
      try {
        output = fs.readFileSync(outPath, 'utf-8')
      } catch {
        /* file may have been removed or unreadable */
      }
      try {
        exitCode = parseInt(fs.readFileSync(rcPath, 'utf-8').trim(), 10) || 0
      } catch {
        exitCode = -1
      }
      try {
        fs.unlinkSync(outPath)
        fs.unlinkSync(rcPath)
        fs.unlinkSync(donePath)
      } catch {
        /* ignore */
      }
      return { output, exitCode }
    }
    await new Promise((r) => setTimeout(r, 150))
  }
  log(`sudoBridge: timeout after ${timeoutMs}ms for inner=${inner.substring(0, 60)}…`)
  return null
}

/** Wait for the keepalive terminal's ready sentinel. */
export async function waitForKeepaliveReady(timeoutMs = 60_000): Promise<boolean> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (fs.existsSync(KEEPALIVE_READY)) return true
    await new Promise((r) => setTimeout(r, 250))
  }
  return false
}

/**
 * Ensure the keepalive is active. If not, trigger cmk.omdAuth and wait for
 * the ready sentinel. Returns true if a usable bridge is available afterwards.
 */
export async function ensureKeepaliveAuth(): Promise<boolean> {
  if (hasKeepalive()) return true
  const pick = await vscode.window.showInformationMessage(
    'This OMD action needs sudo. Authenticate once to reuse the session for all OMD commands for the next hour.',
    'Authenticate'
  )
  if (pick !== 'Authenticate') return false
  await vscode.commands.executeCommand('cmk.omdAuth')
  return waitForKeepaliveReady()
}

/** Clear the ready sentinel. Called when the keepalive terminal closes or a new auth starts. */
export function clearKeepaliveReady(): void {
  try {
    fs.unlinkSync(KEEPALIVE_READY)
  } catch {
    /* ignore */
  }
}
