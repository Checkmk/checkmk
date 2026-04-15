/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { log, notifyInfo } from './core/log'
import { versionNewer } from './core/version'

const STATE_KEY = 'cmk.lastShownWhatsNewVersion'

function listChangelogVersions(extensionPath: string): string[] {
  const dir = path.join(extensionPath, 'changelog')
  if (!fs.existsSync(dir)) return []
  return fs
    .readdirSync(dir)
    .filter((f) => /^v\d+\.\d+\.\d+\.md$/.test(f))
    .map((f) => f.slice(1, -3))
}

async function showWhatsNewSince(
  context: vscode.ExtensionContext,
  sinceVersion: string,
  inclusive: boolean
): Promise<boolean> {
  const currentVersion = context.extension.packageJSON.version as string
  const versions = listChangelogVersions(context.extensionPath)
    .filter((v) => {
      const newerThanSince = inclusive
        ? !versionNewer(sinceVersion, v) // v >= sinceVersion
        : versionNewer(v, sinceVersion) // v > sinceVersion
      return newerThanSince && !versionNewer(v, currentVersion)
    })
    .sort((a, b) => (versionNewer(a, b) ? -1 : 1))

  if (versions.length === 0) return false

  const fragments = versions.map((v) =>
    fs.readFileSync(path.join(context.extensionPath, 'changelog', `v${v}.md`), 'utf8').trim()
  )
  const headerRange = inclusive
    ? `_v${sinceVersion} → v${currentVersion}_`
    : `_v${sinceVersion} → v${currentVersion}_`
  const content = `# What's New in CMK Dev Tools\n\n${headerRange}\n\n${fragments.join('\n\n')}\n`

  const tmpFile = path.join(
    os.tmpdir(),
    `cmk-whats-new-from-v${sinceVersion}-to-v${currentVersion}.md`
  )
  fs.writeFileSync(tmpFile, content, 'utf8')
  await vscode.commands.executeCommand('markdown.showPreview', vscode.Uri.file(tmpFile))
  return true
}

export async function showWhatsNewIfNeeded(context: vscode.ExtensionContext): Promise<void> {
  const currentVersion = context.extension.packageJSON.version as string
  const lastShown = context.globalState.get<string>(STATE_KEY)

  if (!lastShown) {
    await context.globalState.update(STATE_KEY, currentVersion)
    return
  }

  if (!versionNewer(currentVersion, lastShown)) return

  const shown = await showWhatsNewSince(context, lastShown, false)
  await context.globalState.update(STATE_KEY, currentVersion)
  if (shown) {
    log(`Showed What's New since v${lastShown}`)
  }
}

export function registerWhatsNew(context: vscode.ExtensionContext): vscode.Disposable[] {
  return [
    vscode.commands.registerCommand('cmk.showWhatsNew', async () => {
      const currentVersion = context.extension.packageJSON.version as string
      const versions = listChangelogVersions(context.extensionPath).sort((a, b) =>
        versionNewer(a, b) ? -1 : 1
      )
      if (versions.length === 0) {
        notifyInfo('CMK: No changelog files bundled with this extension.')
        return
      }
      const fragments = versions.map((v) =>
        fs.readFileSync(path.join(context.extensionPath, 'changelog', `v${v}.md`), 'utf8').trim()
      )
      const content = `# What's New in CMK Dev Tools\n\n_All versions_\n\n${fragments.join('\n\n')}\n`
      const tmpFile = path.join(os.tmpdir(), `cmk-whats-new-all-v${currentVersion}.md`)
      fs.writeFileSync(tmpFile, content, 'utf8')
      await vscode.commands.executeCommand('markdown.showPreview', vscode.Uri.file(tmpFile))
    }),
    vscode.commands.registerCommand('cmk.pickChangelog', async () => {
      const currentVersion = context.extension.packageJSON.version as string
      const versions = listChangelogVersions(context.extensionPath).sort((a, b) =>
        versionNewer(a, b) ? -1 : 1
      )
      if (versions.length === 0) {
        notifyInfo('CMK: No changelog files bundled with this extension.')
        return
      }
      const items = versions.map((v) => ({
        label: `Since v${v}`,
        description:
          v === currentVersion ? '(current — only this version)' : `→ v${currentVersion}`,
        version: v
      }))
      const pick = await vscode.window.showQuickPick(items, {
        placeHolder: 'Show What\u2019s New starting from which version?'
      })
      if (!pick) return
      const shown = await showWhatsNewSince(context, pick.version, true)
      if (!shown) {
        notifyInfo(`CMK: No changelog entries between v${pick.version} and v${currentVersion}.`)
      }
    }),
    vscode.commands.registerCommand('cmk.whatsNew.reset', async () => {
      const input = await vscode.window.showInputBox({
        prompt: 'Reset cmk.lastShownWhatsNewVersion to (e.g. 0.1.50, or empty to clear)',
        value: '0.1.50'
      })
      if (input === undefined) return
      const value = input.trim() === '' ? undefined : input.trim()
      await context.globalState.update(STATE_KEY, value)
      notifyInfo(`CMK: lastShownWhatsNewVersion reset to ${value ?? '<unset>'}`)
    })
  ]
}
