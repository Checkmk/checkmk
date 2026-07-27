/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { type Edition, FREE_EDITION, availableEditions } from '../core/editions'
import { log } from '../core/log'
import { runCommand, waitForTask } from '../core/tasks'
import { detectOmdSites, triggerOmdRefresh } from './omd'

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

/**
 * Map an OMD site's edition tag (as parsed by `detectOmdSites`, which yields the
 * short codes cre/cce/cme/pro or already-long names) to a `--cmk_edition` value.
 * Legacy `cee` (enterprise) is intentionally absent: it predates the pro/ultimate
 * split and can't be mapped unambiguously, so such sites fall through to no flag.
 */
const SITE_EDITION_TO_CMK: Record<string, Edition> = {
  cre: 'community',
  community: 'community',
  pro: 'pro',
  ultimate: 'ultimate',
  cme: 'ultimatemt',
  ultimatemt: 'ultimatemt',
  cce: 'cloud',
  cloud: 'cloud'
}

/**
 * The `--cmk_edition` value to pin on the outer `bazel run` so its edition matches
 * the target site's. Without this the wrapper uses bazel's default edition while
 * cmk-dev-deploy pins the site edition on its own bazel calls, so every deploy
 * flips the server config and discards the analysis cache. Clamped to what this
 * checkout can build; returns undefined (→ no flag, current behavior) when the
 * site edition is unknown or unmappable.
 */
function resolveDeployEdition(siteName: string): Edition | undefined {
  const raw = detectOmdSites().find((s) => s.name === siteName)?.edition
  if (!raw) return undefined
  const mapped = SITE_EDITION_TO_CMK[raw]
  if (!mapped) return undefined
  const available = availableEditions()
  if (available.includes(mapped)) return mapped
  log(
    `OMD Deploy: ${siteName} is a '${mapped}' site but this checkout builds only ` +
      `${available.join('/')} — clamping to ${FREE_EDITION}`
  )
  void vscode.window.showWarningMessage(
    `cmk-dev-deploy: '${siteName}' is a ${mapped} site, but this checkout can only ` +
      `build ${FREE_EDITION}. Deploying clamped to ${FREE_EDITION}.`
  )
  return FREE_EDITION
}

export async function deployToSite(siteName: string): Promise<void> {
  const pick = await vscode.window.showQuickPick(MODES, {
    placeHolder: `cmk-dev-deploy → ${siteName}`
  })
  if (!pick) return

  const flags = ['-v', '--site', siteName]
  if (pick.mode === 'watch') flags.push('--watch')
  if (pick.mode === 'dry-run') flags.push('--dry-run')

  const edition = resolveDeployEdition(siteName)
  const editionArg = edition ? `--cmk_edition=${edition} ` : ''
  const cmd = `bazel run ${editionArg}${DEPLOY_TARGET} -- ${flags.join(' ')}`
  log(`OMD Deploy ${pick.mode}: ${siteName}`)
  const exec = runCommand(`Deploy → ${siteName} (${pick.mode})`, cmd)
  if (!exec) return

  // --watch runs until the user kills the terminal; don't block on it.
  if (pick.mode === 'watch') return
  await waitForTask(exec)
  triggerOmdRefresh()
}
