/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as vscode from 'vscode'

import type { BuildStatus } from '../build/buildStatus'
import type { DevSiteToolsState } from '../omd/devSiteTools'
import type { OmdSiteWithStatus } from '../omd/omd'
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

export interface StateCache {
  buildStatus: BuildStatus
  profiles: ProfileInfo[]
  commands: Record<string, unknown>
  pythonEnvsActive: boolean
  environment: EnvironmentInfo
  extensionHealth: ExtensionFamily[]
  settingsMismatches: SettingsMismatch[]
  omdSites: OmdSiteWithStatus[]
  devSiteTools: DevSiteToolsState
  onboarding: OnboardingState
  onboardingDismissed: boolean
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
