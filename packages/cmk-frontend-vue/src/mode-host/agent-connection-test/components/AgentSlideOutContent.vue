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

import usei18n from '@/lib/i18n'

import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'
import type { AgentSlideOutTabs } from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

const props = defineProps<{
  allAgentsUrl: string
  legacyAgentUrl: string | undefined
  hostName: string
  agentInstallCmds: AgentInstallCmds
  agentRegistrationCmds: AgentRegistrationCmds
  closeButtonTitle: string
  saveHost: boolean
  agentInstalled: boolean
  isPushMode: boolean
}>()

const { _t } = usei18n()

const legacyInstallTitle = _t('Install the legacy Checkmk agent')

export type PackageOption = {
  label: 'RPM' | 'DEB' | 'TGZ'
  value: 'rpm' | 'deb' | 'tgz'
}
export type PackageOptions = PackageOption[]
const toggleButtonOptions: PackageOptions = [
  { label: 'RPM', value: 'rpm' },
  { label: 'DEB', value: 'deb' },
  { label: 'TGZ', value: 'tgz' }
]
const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

const tabs: AgentSlideOutTabs[] = [
  {
    id: 'windows',
    title: _t('Windows'),
    installMsg: _t(
      'Run this command on your Windows host to download and install the Checkmk agent.'
    ),
    installCmd: props.agentInstallCmds.windows,
    registrationMsg: _t(
      'After you have downloaded the agent, run this command on your Windows host to register the Checkmk agent controller.'
    ),
    registrationCmd: props.agentRegistrationCmds.windows.replace('[HOSTNAME]', props.hostName)
  },
  {
    id: 'linux',
    title: _t('Linux'),
    installMsg: _t(
      'Run this command on your Linux host to download and install the Checkmk agent.'
    ),
    installDebCmd: props.agentInstallCmds.linux_deb,
    installRpmCmd: props.agentInstallCmds.linux_rpm,
    installTgzCmd: props.agentInstallCmds.linux_tgz,
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
      'After you have downloaded the agent, run this command on your Linux host to register the Checkmk agent controller.'
    ),
    registrationCmd: props.agentRegistrationCmds.linux.replace('[HOSTNAME]', props.hostName),
    toggleButtonOptions: toggleButtonOptions
  },
  {
    id: 'solaris',
    title: _t('Solaris'),
    installMsg: _t('Run this command on your Solaris host to download the Checkmk agent.'),
    installCmd: props.agentInstallCmds.solaris,
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
      'After you have downloaded the agent, run this command on your Solaris host to install the Checkmk agent.'
    ),
    registrationCmd: props.agentRegistrationCmds.solaris.replace('[HOSTNAME]', props.hostName)
  },
  {
    id: 'aix',
    title: _t('AIX'),
    installMsg: _t('Run this command on your AIX host to download and install the Checkmk agent.'),
    installCmd: props.agentInstallCmds.aix,
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
      'After you have downloaded the agent, run this command on your AIX host to register the Checkmk agent controller.'
    ),
    registrationCmd: props.agentRegistrationCmds.aix.replace('[HOSTNAME]', props.hostName)
  }
]
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
    :close-button-title="closeButtonTitle"
    :save-host="saveHost"
    :agent-installed="agentInstalled"
    :host-name="hostName"
    :is-push-mode="isPushMode"
    @close="close"
  />
</template>
