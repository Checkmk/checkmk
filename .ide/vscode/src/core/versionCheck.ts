/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

const IDE_EXTENSION_DIR = path.join('.ide', 'vscode')
const BAZEL_TARGET = `//${IDE_EXTENSION_DIR}:vsix`
const VSIX_PATH = `bazel-bin/${IDE_EXTENSION_DIR}/cmk-vscode.vsix`

function getWorkspaceVersion(): string | undefined {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return undefined

  const pkgPath = path.join(wsPath, IDE_EXTENSION_DIR, 'package.json')
  if (!fs.existsSync(pkgPath)) return undefined

  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'))
  return pkg.version
}

function resolveProfile(): string {
  return `$(python3 -c "
import json, os
storage = os.path.expanduser('~/.config/Code/User/globalStorage/storage.json')
with open(storage) as f: d = json.load(f)
ws = 'file://' + os.path.realpath('.')
assoc = d.get('profileAssociations', {}).get('workspaces', {})
pid = assoc.get(ws, '__default__profile__')
if pid == '__default__profile__':
    print('Default')
else:
    profiles = {p['location']: p['name'] for p in d.get('userDataProfiles', [])}
    print(profiles.get(pid, 'Default'))
")`
}

export function rebuildExtension(): void {
  const terminal = vscode.window.createTerminal('CMK Extension Update')
  const profile = resolveProfile()
  terminal.sendText(
    `bazel build ${BAZEL_TARGET} && ` +
      `code --profile "${profile}" --install-extension ${VSIX_PATH} --force`
  )
  terminal.show()
}

function promptRebuild(installedVersion: string, wsVersion: string): void {
  vscode.window
    .showWarningMessage(
      `CMK Extension: installed v${installedVersion} ≠ workspace v${wsVersion}`,
      'Rebuild & Install'
    )
    .then((choice) => {
      if (choice === 'Rebuild & Install') {
        rebuildExtension()
      }
    })
}

export interface VersionMismatch {
  installed: string
  workspace: string
}

export function getVersionMismatch(context: vscode.ExtensionContext): VersionMismatch | null {
  const installed: string = context.extension.packageJSON.version
  const workspace = getWorkspaceVersion()
  if (workspace && workspace !== installed) {
    return { installed, workspace }
  }
  return null
}

export function checkVersionMismatch(context: vscode.ExtensionContext): void {
  const installedVersion: string = context.extension.packageJSON.version
  const wsVersion = getWorkspaceVersion()

  if (wsVersion && wsVersion !== installedVersion) {
    promptRebuild(installedVersion, wsVersion)
  }

  // Watch for changes (e.g. git pull, branch switch)
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (wsPath) {
    const watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(wsPath, `${IDE_EXTENSION_DIR}/package.json`)
    )
    watcher.onDidChange(() => {
      const newWsVersion = getWorkspaceVersion()
      if (newWsVersion && newWsVersion !== installedVersion) {
        promptRebuild(installedVersion, newWsVersion)
      }
    })
    context.subscriptions.push(watcher)
  }
}
