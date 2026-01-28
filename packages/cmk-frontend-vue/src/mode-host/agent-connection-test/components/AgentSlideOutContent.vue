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
import type { TranslatedString } from '@/lib/i18nString'

import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

import type { AgentSlideOutTabs, PackageOptions } from '../lib/type_def'

const props = defineProps<{
  allAgentsUrl: string
  legacyAgentUrl: string | undefined
  hostName: string
  siteId: string
  siteServer: string
  agentInstallCmds: AgentInstallCmds
  agentRegistrationCmds: AgentRegistrationCmds
  closeButtonTitle: TranslatedString
  saveHost: boolean
  hostExists: boolean
  setupError: boolean
  agentInstalled: boolean
  isPushMode: boolean
}>()

const { _t } = usei18n()

const legacyInstallTitle = _t('Install the legacy Checkmk agent')

const toggleButtonOptions: PackageOptions = [
  { label: 'RPM', value: 'rpm' },
  { label: 'DEB', value: 'deb' },
  { label: 'TGZ', value: 'tgz' }
]
const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

function replaceMacros(cmd: string | undefined, isRegistration: boolean) {
  if (!cmd) {
    return ''
  }

  cmd = cmd.replace(/{{HOSTNAME}}/g, props.hostName ?? '').replace(/{{SITE}}/g, props.siteId ?? '')
  if (isRegistration) {
    return cmd.replace(/{{SERVER}}/g, props.siteServer || window.location.host)
  }

  return cmd.replace(
    /{{SERVER}}/g,
    props.siteServer || `${window.location.protocol}//${window.location.host}`
  )
}

const tabs: AgentSlideOutTabs[] = [
  {
    id: 'windows',
    title: _t('Windows'),
    installMsg: _t(
      'Run this command on your Windows host to download and install the Checkmk agent. Please make sure to run this command with sufficient permissions (e.g. “Run as Administrator”)'
    ),
    installCmd: replaceMacros(props.agentInstallCmds.windows, false),
    registrationMsg: _t(
      'After you have downloaded the agent, run this command on your Windows host to register the Checkmk agent controller. Please make sure to run this command with sufficient permissions (e.g. “Run as Administrator”).'
    ),
    registrationCmd: replaceMacros(props.agentRegistrationCmds.windows, true)
  },
  {
    id: 'linux',
    title: _t('Linux'),
    installMsg: _t(
      'Run this command on your Linux host to download and install the Checkmk agent.'
    ),
    installDebCmd: replaceMacros(props.agentInstallCmds.linux_deb, false),
    installRpmCmd: replaceMacros(props.agentInstallCmds.linux_rpm, false),
    installTgzCmd: replaceMacros(props.agentInstallCmds.linux_tgz, false),
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
    registrationCmd: replaceMacros(props.agentRegistrationCmds.linux, true),
    toggleButtonOptions: toggleButtonOptions
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
      'After you have downloaded the agent, run this command on your Solaris host to install the Checkmk agent.'
    ),
    registrationCmd: replaceMacros(props.agentRegistrationCmds.solaris, true)
  },
  {
    id: 'aix',
    title: _t('AIX'),
    installMsg: _t('Run this command on your AIX host to download and install the Checkmk agent.'),
    installCmd: replaceMacros(props.agentInstallCmds.aix, false),
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
    registrationCmd: replaceMacros(props.agentRegistrationCmds.aix, true)
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
    :host-exists="hostExists"
    :setup-error="setupError"
    :agent-installed="agentInstalled"
    :host-name="hostName"
    :is-push-mode="isPushMode"
    @close="close"
  />
</template>
