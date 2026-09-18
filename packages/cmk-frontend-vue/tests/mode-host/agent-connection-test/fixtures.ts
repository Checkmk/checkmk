/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  AgentInstallCmds,
  AgentRegistrationCmds,
  AgentStatusCmds
} from 'cmk-shared-typing/typescript/agent_slideout'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type AgentSlideOutContent from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'

/**
 * Command templates shaped like the ones the backend actually emits (see
 * `cmk/gui/agent_commands.py`): install commands carry `{{SERVER}}`/`{{SITE}}`
 * and the `[AGENT_DOWNLOAD_OTT]` placeholder, registration commands carry
 * `{{HOSTNAME}}`/`{{SERVER}}`/`{{SITE}}` and `--user agent_registration`.
 */
export const installCmds: AgentInstallCmds = {
  windows_download: 'cmd-download {{SERVER}}/{{SITE}} 0:[AGENT_DOWNLOAD_OTT]',
  windows_download_powershell: 'ps-download {{SERVER}}/{{SITE}} 0:[AGENT_DOWNLOAD_OTT]',
  windows: 'cmd-install check-mk-agent.msi',
  windows_powershell: 'ps-install check-mk-agent.msi',
  linux_deb: 'deb-install {{SERVER}}/{{SITE}} 0:[AGENT_DOWNLOAD_OTT]',
  linux_rpm: 'rpm-install {{SERVER}}/{{SITE}} 0:[AGENT_DOWNLOAD_OTT]',
  linux_tgz_download: 'tgz-download {{SERVER}}/{{SITE}} 0:[AGENT_DOWNLOAD_OTT]',
  linux_tgz_extract: 'tgz-extract check-mk-agent.tar.gz',
  solaris: 'solaris-install {{SERVER}}/{{SITE}} 0:[AGENT_DOWNLOAD_OTT]',
  aix_download: 'aix-download {{SERVER}}/{{SITE}} 0:[AGENT_DOWNLOAD_OTT]',
  aix_extract: 'aix-extract check-mk-agent.tar.gz'
}

const registerCmd = (prefix: string) =>
  `${prefix}-register --hostname {{HOSTNAME}} --server {{SERVER}} --site {{SITE}} --user agent_registration`

export const registrationCmds: AgentRegistrationCmds = {
  windows: registerCmd('cmd'),
  windows_powershell: registerCmd('ps'),
  linux: registerCmd('linux'),
  solaris: registerCmd('solaris'),
  aix: registerCmd('aix')
}

export const statusCmds: AgentStatusCmds = {
  windows: 'cmd-status',
  windows_powershell: 'ps-status',
  linux: 'linux-status',
  solaris: 'solaris-status',
  aix: 'aix-status'
}

/**
 * Props for `AgentSlideOutContent` — the seam both real consumers instantiate
 * (`AgentConnectionTest.vue` and `src/setup/AgentDownloadDialog.vue`).
 */
export type ContentProps = InstanceType<typeof AgentSlideOutContent>['$props']

export const contentProps: ContentProps = {
  allAgentsUrl: 'https://example.test/all-agents',
  userSettingsUrl: 'https://example.test/user-settings',
  legacyAgentUrl: undefined,
  hostName: 'test-host',
  siteId: 'test-site',
  siteServer: 'https://monitoring.example.test',
  agentReceiverPort: 8000,
  agentReceiverPortIsDefault: false,
  agentInstallCmds: installCmds,
  agentRegistrationCmds: registrationCmds,
  agentStatusCmds: statusCmds,
  closeButtonTitle: 'Close & test connection' as TranslatedString,
  saveHost: false,
  hostExists: true,
  setupError: false,
  agentInstalled: false,
  isPushMode: false,
  unbakedFallback: null
}
