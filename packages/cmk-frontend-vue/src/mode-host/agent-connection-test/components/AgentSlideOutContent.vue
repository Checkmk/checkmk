<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type AgentInstallCmds,
  type AgentRegistrationCmds
} from 'cmk-shared-typing/typescript/agent_slideout'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

import type { AgentSlideOutTabs } from '../lib/type_def'

const props = defineProps<{
  allAgentsUrl: string
  userSettingsUrl: string
  legacyAgentUrl: string | undefined
  hostName: string
  siteId: string
  siteServer: string
  agentReceiverPort: number
  agentReceiverPortIsDefault: boolean
  agentInstallCmds: AgentInstallCmds
  agentRegistrationCmds: AgentRegistrationCmds
  closeButtonTitle: TranslatedString
  saveHost: boolean
  hostExists: boolean
  setupError: boolean
  agentInstalled: boolean
  isPushMode: boolean
  canDownloadBakedAgents: boolean
}>()

const { _t } = usei18n()

const legacyInstallTitle = _t('Install the legacy Checkmk agent')
const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

function registrationServer(): string {
  let host: string
  if (props.siteServer) {
    try {
      host = new URL(props.siteServer).hostname
    } catch {
      host = props.siteServer
    }
  } else {
    host = window.location.hostname
  }
  return `${host}:${props.agentReceiverPort}`
}

function replaceMacros(cmd: string | undefined, isRegistration: boolean) {
  if (!cmd) {
    return ''
  }

  cmd = cmd.replace(/{{HOSTNAME}}/g, props.hostName ?? '').replace(/{{SITE}}/g, props.siteId ?? '')
  if (isRegistration) {
    return cmd.replace(/{{SERVER}}/g, registrationServer())
  }

  return cmd.replace(
    /{{SERVER}}/g,
    props.siteServer || `${window.location.protocol}//${window.location.host}`
  )
}

const tabs = computed<AgentSlideOutTabs[]>(() => [
  {
    id: 'windows',
    title: _t('Windows'),
    installMsg: _t(
      'Run these commands on your Windows host to download and install the Checkmk agent. Please make sure to run these commands with sufficient permissions (e.g. "Run as Administrator")'
    ),
    installDownloadCmd: replaceMacros(props.agentInstallCmds.windows_download, false),
    installCmd: replaceMacros(props.agentInstallCmds.windows, false),
    registrationMsg: _t(
      'After you have installed the agent, run this command on your Windows host to register the Checkmk agent controller. Please make sure to run this command with sufficient permissions (e.g. "Run as Administrator").'
    ),
    registrationCmd: replaceMacros(props.agentRegistrationCmds.windows, true)
  },
  {
    id: 'linux',
    title: _t('Linux'),
    installUrl: props.legacyAgentUrl
      ? {
          title: legacyInstallTitle,
          url: props.legacyAgentUrl,
          msg: _t(
            'If you want to install the Checkmk agent on Linux, please read how to install the legacy agent'
          ),
          icon: 'learning-guide'
        }
      : undefined,
    registrationMsg: _t(
      'After you have installed the agent, run this command on your Linux host to register the Checkmk agent controller.'
    ),
    registrationCmd: replaceMacros(props.agentRegistrationCmds.linux, true),
    subTabs: [
      {
        id: 'deb',
        label: 'DEB',
        installMsg: _t(
          'Run this command on your Linux host to download and install the Checkmk agent.'
        ),
        installCmd: replaceMacros(props.agentInstallCmds.linux_deb, false)
      },
      {
        id: 'rpm',
        label: 'RPM',
        installMsg: _t(
          'Run this command on your Linux host to download and install the Checkmk agent.'
        ),
        installCmd: replaceMacros(props.agentInstallCmds.linux_rpm, false)
      },
      {
        id: 'tgz',
        label: 'TGZ',
        installMsg: _t(
          'Run these commands on your Linux host to download and install the Checkmk agent.'
        ),
        downloadCmd: replaceMacros(props.agentInstallCmds.linux_tgz_download, false),
        installWarning: _t(
          'This command extracts files directly into the root directory (/). Make sure you are executing this command on the correct host.'
        ),
        installCmd: replaceMacros(props.agentInstallCmds.linux_tgz_extract, false)
      }
    ]
  },
  {
    id: 'solaris',
    title: _t('Solaris'),
    installMsg: _t('Run this command on your Solaris host to download the Checkmk agent.'),
    installCmd: replaceMacros(props.agentInstallCmds.solaris, false),
    installUrl: props.legacyAgentUrl
      ? {
          title: legacyInstallTitle,
          url: props.legacyAgentUrl,
          msg: _t(
            'If you want to install the Checkmk agent on Solaris, please read how to install the legacy agent'
          ),
          icon: 'learning-guide'
        }
      : undefined,
    registrationMsg: _t(
      'After you have installed the agent, run this command on your Solaris host to register the Checkmk agent.'
    ),
    registrationCmd: replaceMacros(props.agentRegistrationCmds.solaris, true)
  },
  {
    id: 'aix',
    title: _t('AIX'),
    installMsg: _t(
      'Run these commands on your AIX host to download and install the Checkmk agent.'
    ),
    installWarning: _t(
      'This command extracts files directly into the root directory (/). Make sure you are executing this command on the correct host.'
    ),
    installDownloadCmd: replaceMacros(props.agentInstallCmds.aix_download, false),
    installCmd: replaceMacros(props.agentInstallCmds.aix_extract, false),
    installUrl: props.legacyAgentUrl
      ? {
          title: legacyInstallTitle,
          url: props.legacyAgentUrl,
          msg: _t(
            'If you want to install the Checkmk agent on AIX, please read how to install the legacy agent'
          ),
          icon: 'learning-guide'
        }
      : undefined,
    registrationMsg: _t(
      'After you have installed the agent, run this command on your AIX host to register the Checkmk agent controller.'
    ),
    registrationCmd: replaceMacros(props.agentRegistrationCmds.aix, true)
  }
])
</script>

<template>
  <AgentSlideOut
    :dialog-msg="
      _t(
        `To monitor systems like Linux or Windows with Checkmk, you need to install an agent on these systems.
           This agent acts as a small program that collects data about the systems state, such as how much storage is used or the CPU load.`
      )
    "
    :tabs="tabs"
    :all-agents-url="allAgentsUrl"
    :user-settings-url="userSettingsUrl"
    :close-button-title="closeButtonTitle"
    :save-host="saveHost"
    :host-exists="hostExists"
    :setup-error="setupError"
    :agent-installed="agentInstalled"
    :host-name="hostName"
    :is-push-mode="isPushMode"
    :agent-receiver-port-is-default="agentReceiverPortIsDefault"
    :can-download-baked-agents="canDownloadBakedAgents"
    @close="close"
  />
</template>
