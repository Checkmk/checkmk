/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { notifyError, notifyInfo } from './log'
import { runCommand, waitForTask } from './tasks'
import { versionNewer } from './version'

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

// The extension is loaded into the *active* profile, so its globalStorageUri
// encodes the profile location:
//   default: <userDataDir>/User/globalStorage/<extId>
//   custom : <userDataDir>/User/profiles/<profile-id>/globalStorage/<extId>
// The display name (what `code --profile` accepts) is mapped via storage.json.
function resolveActiveProfile(context: vscode.ExtensionContext): string {
  const storage = context.globalStorageUri.fsPath
  const parts = storage.split(/[/\\]profiles[/\\]/)
  if (parts.length < 2) return 'Default'

  const profileLocation = parts[1].split(/[/\\]/)[0]
  const userDir = parts[0]
  const storageJson = path.join(userDir, 'globalStorage', 'storage.json')
  if (!fs.existsSync(storageJson)) return 'Default'

  try {
    const data = JSON.parse(fs.readFileSync(storageJson, 'utf8'))
    const profiles = (data.userDataProfiles ?? []) as Array<{ location: string; name: string }>
    return profiles.find((p) => p.location === profileLocation)?.name ?? 'Default'
  } catch {
    return 'Default'
  }
}

export async function rebuildExtension(context: vscode.ExtensionContext): Promise<void> {
  const profile = resolveActiveProfile(context)
  const cmd =
    `bazel build ${BAZEL_TARGET} && ` +
    `code --profile "${profile}" --install-extension ${VSIX_PATH} --force`

  const exec = runCommand('CMK Extension Update', cmd)
  if (!exec) return

  const exitCode = await waitForTask(exec)
  if (exitCode !== 0) {
    notifyError(
      'CMK Extension install failed',
      `Profile: ${profile} — exit code: ${exitCode ?? 'unknown'}`
    )
    return
  }

  const choice = await notifyInfo(
    'CMK Extension installed. Reload window to activate the new version.',
    `Profile: ${profile}`,
    'Reload Window'
  )
  if (choice === 'Reload Window') {
    vscode.commands.executeCommand('workbench.action.reloadWindow')
  }
}

function promptRebuild(
  context: vscode.ExtensionContext,
  installedVersion: string,
  wsVersion: string
): void {
  vscode.window
    .showWarningMessage(
      `CMK Extension: installed v${installedVersion} ≠ workspace v${wsVersion}`,
      'Install'
    )
    .then((choice) => {
      if (choice === 'Install') {
        rebuildExtension(context)
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
  if (workspace && versionNewer(workspace, installed)) {
    return { installed, workspace }
  }
  return null
}

export function checkVersionMismatch(context: vscode.ExtensionContext): void {
  const installedVersion: string = context.extension.packageJSON.version
  const wsVersion = getWorkspaceVersion()

  if (wsVersion && versionNewer(wsVersion, installedVersion)) {
    promptRebuild(context, installedVersion, wsVersion)
  }

  // Watch for changes (e.g. git pull, branch switch)
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (wsPath) {
    const watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(wsPath, `${IDE_EXTENSION_DIR}/package.json`)
    )
    watcher.onDidChange(() => {
      const newWsVersion = getWorkspaceVersion()
      if (newWsVersion && versionNewer(newWsVersion, installedVersion)) {
        promptRebuild(context, installedVersion, newWsVersion)
      }
    })
    context.subscriptions.push(watcher)
  }
}
