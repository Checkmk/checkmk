/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as vscode from 'vscode'

import type { BuildStatus } from '../build/buildStatus'
import type { VersionMismatch } from '../core/versionCheck'
import type { DevSiteToolsState } from '../omd/devSiteTools'
import type { OmdSiteWithStatus } from '../omd/omd'
import type { ProxyInfo } from '../omd/proxy'
import type { ProfileInfo } from '../profiles/profileManager'

export interface EnvironmentInfo {
  python: string
  pythonPath: string
  node: string
  bazel: string
  bazelisk: string
  docker: string
  gcc: string
  pyenv: boolean
  systemReady: boolean
}

export interface OnboardingState {
  systemDone: boolean
  venvDone: boolean
  ideDone: boolean
  currentStep: string | null
  allDone: boolean
}

export interface ExtensionHealthEntry {
  id: string
  installed: boolean
}

export interface ExtensionFamily {
  name: string
  displayName: string
  required: boolean
  extensions: ExtensionHealthEntry[]
  allInstalled: boolean
  installedCount: number
}

export interface SettingsMismatch {
  key: string
  expected: unknown
  actual: unknown
  family: string
  scope: string
}

export interface MypyTargetsInfo {
  enabled: boolean
  pythonProfileActive: boolean
  activeCount: number
  catalogSize: number
  activeTargets: string[]
  baselineTargets: string[]
  alwaysOnTargets: string[]
  stagedActiveAdd: string[]
  stagedActiveRemove: string[]
  stagedBaselineAdd: string[]
  stagedBaselineRemove: string[]
  catalog: string[]
}

export interface AllocatorInfo {
  mode: 'default' | 'jemalloc'
  libraryAvailable: boolean
  recommendationDismissed: boolean
  wrapperExists: boolean
  dmypyExecutableMatches: boolean
  runUsingInterpreterOff: boolean
}

export interface PylanceHealthInfo {
  pid: number | null
  rssMiB: number | null
  thresholdMiB: number
  overThreshold: boolean
}

export interface StateCache {
  buildStatus: BuildStatus
  profiles: ProfileInfo[]
  commands: Record<string, unknown>
  pythonEnvsActive: boolean
  environment: EnvironmentInfo
  extensionHealth: ExtensionFamily[]
  settingsMismatches: SettingsMismatch[]
  omdSites: OmdSiteWithStatus[]
  activeProxies: ProxyInfo[]
  devSiteTools: DevSiteToolsState
  versionMismatch: VersionMismatch | null
  onboarding: OnboardingState
  onboardingDismissed: boolean
  configInWorkspace: boolean
  mypyTargets: MypyTargetsInfo
  allocator: AllocatorInfo
  pylanceHealth: PylanceHealthInfo
}

export interface SectionContext {
  refreshAll: () => void
  showSectionLoading: (...sections: string[]) => void
}

export interface WebviewMessage {
  type: string
  [key: string]: unknown
}

export interface SectionModule {
  render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string
  handleMessage(msg: WebviewMessage, ctx: SectionContext): Promise<boolean>
}
