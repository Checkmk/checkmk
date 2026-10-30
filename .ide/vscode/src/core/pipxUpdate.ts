/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { shellEscape } from './config'
import { log } from './log'
import { safeExecAsync } from './shell'
import { getExtendedPath, runCommand, waitForTask } from './tasks'
import { versionNewer } from './version'

export interface PipxInstall {
  version: string
  global: boolean
}

/** Once a day, compares a pipx-installed package with its newest PyPI release
 *  and offers the upgrade. A `pipx install --global` copy (venvs under
 *  /opt/pipx, shims in /usr/local/bin) is invisible to the per-user pipx home,
 *  so it is upgraded with `sudo pipx upgrade --global` — a plain
 *  `pipx upgrade` would silently no-op. */
export class PipxUpdateCheck {
  private static readonly CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000

  constructor(
    private readonly pkg: string,
    private readonly lastCheckKey: string
  ) {}

  static parseVersion(listing: string, pkg: string): string {
    for (const line of listing.split('\n')) {
      const [name, version] = line.trim().split(/\s+/)
      if (name === pkg && version) return version
    }
    return ''
  }

  static parsePypiVersion(raw: string): string {
    try {
      return JSON.parse(raw).info?.version || ''
    } catch {
      return ''
    }
  }

  static upgradeCommand(pkg: string, global: boolean): string {
    return global ? `sudo pipx upgrade --global ${pkg}` : `pipx upgrade ${pkg}`
  }

  async run(context: vscode.ExtensionContext): Promise<void> {
    const lastCheck = context.globalState.get<number>(this.lastCheckKey, 0) ?? 0
    if (Date.now() - lastCheck < PipxUpdateCheck.CHECK_INTERVAL_MS) return

    const install = await this.installed()
    if (!install) return

    const latest = await this.latestPypiVersion()
    void context.globalState.update(this.lastCheckKey, Date.now())
    if (!latest || !versionNewer(latest, install.version)) return

    log(`${this.pkg} update available: ${install.version} → ${latest}`)
    const choice = await vscode.window.showInformationMessage(
      `${this.pkg} update available: ${install.version} → ${latest}`,
      'Update'
    )
    if (choice !== 'Update') return
    const command = PipxUpdateCheck.upgradeCommand(this.pkg, install.global)
    log(`Update ${this.pkg}: ${command}`)
    const exec = runCommand(`${this.pkg} update`, command)
    if (exec) await waitForTask(exec)
  }

  async install(): Promise<void> {
    log(`Install ${this.pkg}`)
    const exec = runCommand(`Install ${this.pkg}`, `pipx install ${this.pkg}`)
    if (exec) await waitForTask(exec)
  }

  async available(): Promise<boolean | null> {
    if (await this.installed()) return true
    const env = `PATH=${shellEscape(getExtendedPath())}`
    const [pipx, uvTools] = await Promise.all([
      safeExecAsync(`${env} command -v pipx`),
      safeExecAsync(`${env} uv tool list 2>/dev/null`)
    ])
    if (PipxUpdateCheck.parseVersion(uvTools, this.pkg)) return true
    return pipx ? false : null
  }

  async installed(): Promise<PipxInstall | null> {
    const user = PipxUpdateCheck.parseVersion(
      await safeExecAsync('pipx list --short 2>/dev/null', { timeout: 5000 }),
      this.pkg
    )
    if (user) return { version: user, global: false }
    const global = PipxUpdateCheck.parseVersion(
      await safeExecAsync('pipx list --global --short 2>/dev/null', { timeout: 5000 }),
      this.pkg
    )
    return global ? { version: global, global: true } : null
  }

  private async latestPypiVersion(): Promise<string> {
    const raw = await safeExecAsync(`curl -s https://pypi.org/pypi/${this.pkg}/json 2>/dev/null`, {
      timeout: 10000
    })
    return raw ? PipxUpdateCheck.parsePypiVersion(raw) : ''
  }
}
