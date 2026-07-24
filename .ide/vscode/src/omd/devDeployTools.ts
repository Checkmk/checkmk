/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log } from '../core/log'
import { runCommand, waitForTask } from '../core/tasks'
import { triggerOmdRefresh } from './omd'

type Mode = 'deploy' | 'watch' | 'dry-run'

interface ModeOption extends vscode.QuickPickItem {
  mode: Mode
}

const MODES: ModeOption[] = [
  {
    label: '$(rocket) Deploy',
    description: 'Build and push changed files (one-shot)',
    mode: 'deploy'
  },
  {
    label: '$(eye) Watch',
    description: 'Watch for changes and auto-deploy (runs until terminal is closed)',
    mode: 'watch'
  },
  {
    label: '$(beaker) Dry run',
    description: 'Show what would be deployed without changing anything',
    mode: 'dry-run'
  }
]

const DEPLOY_TARGET = '//packages/cmk-dev-deploy:cmk-dev-deploy-bin'

export async function deployToSite(siteName: string): Promise<void> {
  const pick = await vscode.window.showQuickPick(MODES, {
    placeHolder: `cmk-dev-deploy → ${siteName}`
  })
  if (!pick) return

  const flags = ['-v', '--site', siteName]
  if (pick.mode === 'watch') flags.push('--watch')
  if (pick.mode === 'dry-run') flags.push('--dry-run')

  const cmd = `bazel run ${DEPLOY_TARGET} -- ${flags.join(' ')}`
  log(`OMD Deploy ${pick.mode}: ${siteName}`)
  const exec = runCommand(`Deploy → ${siteName} (${pick.mode})`, cmd)
  if (!exec) return

  // --watch runs until the user kills the terminal; don't block on it.
  if (pick.mode === 'watch') return
  await waitForTask(exec)
  triggerOmdRefresh()
}
