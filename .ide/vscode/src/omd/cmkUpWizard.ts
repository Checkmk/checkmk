/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import type { CmkUp, Playbook, PlaybookRunOptions, PlaybookSource } from './cmkUp'

type RunFlag = Exclude<keyof PlaybookRunOptions, 'phases'>

export type PlaybookRunPreset = Partial<Record<RunFlag, boolean>>

interface PlaybookItem extends vscode.QuickPickItem {
  target?: string
  browse?: boolean
}

interface FlagItem extends vscode.QuickPickItem {
  flag: RunFlag
}

export class PlaybookRunWizard {
  private static readonly SOURCE_LABELS: Readonly<Record<PlaybookSource, string>> = {
    workspace: 'Workspace',
    directory: 'Playbook directories',
    shipped: 'Shipped examples'
  }
  private static readonly FLAGS: readonly FlagItem[] = [
    {
      flag: 'keep',
      label: '--keep',
      description: 'leave versions, sites and objects in place at the end',
      picked: true
    },
    { flag: 'purge', label: '--purge', description: "delete the playbook's host folders first" },
    { flag: 'dryRun', label: '--dry-run', description: 'print every write, change nothing' },
    { flag: 'verify', label: '--verify', description: 'read everything back after applying' }
  ]

  constructor(private readonly cmkUp: CmkUp) {}

  async start(presetTarget?: string, preset?: PlaybookRunPreset): Promise<void> {
    const target = presetTarget ?? (await this.pickPlaybook())
    if (!target) return
    await this.saveIfDirty(target)
    const phases = await this.pickPhases(target)
    if (!phases) return
    const flags = await this.pickFlags(preset)
    if (!flags) return
    await this.cmkUp.run(target, { ...flags, phases })
  }

  private async pickPlaybook(): Promise<string | undefined> {
    const pick = await vscode.window.showQuickPick(this.playbookItems(), {
      title: 'cmk-up: playbook',
      placeHolder: 'Type to filter by name, path or description',
      matchOnDescription: true,
      matchOnDetail: true
    })
    if (!pick?.browse) return pick?.target
    const uris = await vscode.window.showOpenDialog({
      title: 'cmk-up playbook',
      filters: { 'cmk-up playbook': ['yaml', 'yml'] }
    })
    return uris?.[0]?.fsPath
  }

  private async playbookItems(): Promise<PlaybookItem[]> {
    const playbooks = await this.cmkUp.playbooks()
    const items: PlaybookItem[] = [{ label: '$(folder-opened) Browse…', browse: true }]
    for (const source of Object.keys(PlaybookRunWizard.SOURCE_LABELS) as PlaybookSource[]) {
      const ofSource = playbooks.filter((p) => p.source === source)
      if (ofSource.length === 0) continue
      items.push({
        label: PlaybookRunWizard.SOURCE_LABELS[source],
        kind: vscode.QuickPickItemKind.Separator
      })
      items.push(...ofSource.map((p) => this.playbookItem(p)))
    }
    return items
  }

  private playbookItem(playbook: Playbook): PlaybookItem {
    return {
      label: playbook.name,
      description:
        playbook.source === 'shipped' ? undefined : vscode.workspace.asRelativePath(playbook.file),
      detail: playbook.description || undefined,
      target: playbook.target
    }
  }

  private async pickPhases(target: string): Promise<string[] | undefined> {
    const phases = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Window, title: 'cmk-up: reading phases' },
      () => this.cmkUp.listPhases(target)
    )
    if (phases.length <= 1) return []
    const picks = await vscode.window.showQuickPick(
      phases.map((p) => ({ label: p.name, description: p.sites, detail: p.description })),
      {
        title: 'cmk-up: phases',
        placeHolder: 'Tick the phases to run; none ticked runs them all',
        canPickMany: true
      }
    )
    return picks?.map((p) => p.label)
  }

  private async pickFlags(
    preset?: PlaybookRunPreset
  ): Promise<Record<RunFlag, boolean> | undefined> {
    const items = PlaybookRunWizard.FLAGS.map((item) => ({
      ...item,
      picked: preset?.[item.flag] ?? item.picked
    }))
    const picks = await vscode.window.showQuickPick(items, {
      title: 'cmk-up: options',
      canPickMany: true
    })
    if (!picks) return
    const ticked = new Set(picks.map((p) => p.flag))
    return {
      keep: ticked.has('keep'),
      purge: ticked.has('purge'),
      dryRun: ticked.has('dryRun'),
      verify: ticked.has('verify')
    }
  }

  private async saveIfDirty(file: string): Promise<void> {
    const document = vscode.workspace.textDocuments.find((d) => d.fileName === file)
    if (document?.isDirty) await document.save()
  }
}
