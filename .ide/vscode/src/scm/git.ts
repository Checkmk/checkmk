/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { execFile } from 'child_process'
import { promisify } from 'util'
import * as vscode from 'vscode'

import { safeExec } from '../core/shell'

const execFileAsync = promisify(execFile)

export function repoRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

export function currentBranch(cwd: string): string {
  return safeExec('git rev-parse --abbrev-ref HEAD', { cwd })
}

/** Run `git <args>` asynchronously without going through a shell.
 *  Returns trimmed stdout on success, or null on failure. */
export async function gitAsync(cwd: string, args: string[]): Promise<string | null> {
  try {
    const { stdout } = await execFileAsync('git', args, { cwd, maxBuffer: 16 * 1024 * 1024 })
    return stdout.trim()
  } catch {
    return null
  }
}
