/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Saving the host submits the legacy edit-host form, which reloads the page.
 * These keys carry the slideout's state across that reload.
 *
 * `reopenSlideIn` and `slideInAgentInstalled` are read back by
 * `AgentConnectionTest.vue`, which owns the slide-in itself.
 */
const TAB_KEY = 'slideInTabState'
const PACKAGE_KEY = 'slideInModelState'
const REOPEN_KEY = 'reopenSlideIn'
const AGENT_INSTALLED_KEY = 'slideInAgentInstalled'

export interface RestoredSlideoutState {
  tabId: string | null
  packageId: string | null
}

/** Read the state left behind by a save-host reload, consuming it. */
export function takeRestoredState(): RestoredSlideoutState {
  const restored = {
    tabId: sessionStorage.getItem(TAB_KEY),
    packageId: sessionStorage.getItem(PACKAGE_KEY)
  }
  sessionStorage.removeItem(TAB_KEY)
  sessionStorage.removeItem(PACKAGE_KEY)
  return restored
}

export function rememberBeforeSaveHost(state: {
  tabId: string
  packageId: string
  agentInstalled: boolean
}): void {
  sessionStorage.setItem(REOPEN_KEY, 'true')
  sessionStorage.setItem(TAB_KEY, state.tabId)
  sessionStorage.setItem(PACKAGE_KEY, state.packageId)
  sessionStorage.setItem(AGENT_INSTALLED_KEY, String(state.agentInstalled))
}
