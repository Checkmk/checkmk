/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { notifyInfo, notifyWarn } from '../../core/log'

function resolveInterpreterPath(): void {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return

  const venvPython = path.join(wsPath, '.venv', 'bin', 'python')

  try {
    const realPath = fs.realpathSync(venvPython)
    notifyInfo('CMK: Python interpreter verified', realPath)
  } catch {
    notifyWarn('CMK: .venv/bin/python could not be resolved — venv may be broken.')
  }
}

export function registerInterpreterResolver(): vscode.Disposable[] {
  const cmd = vscode.commands.registerCommand('cmk.resolveInterpreter', resolveInterpreterPath)
  return [cmd]
}
