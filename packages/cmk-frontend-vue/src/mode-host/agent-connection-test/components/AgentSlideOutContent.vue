<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import {
  type AgentInstallCmds,
  type AgentRegistrationCmds
} from 'cmk-shared-typing/typescript/agent_slideout'

import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'
import type { AgentSlideOutTabs } from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

const props = defineProps<{
  all_agents_url: string
  legacy_agent_url: string | undefined
  host_name: string
  agent_install_cmds: AgentInstallCmds
  agent_registration_cmds: AgentRegistrationCmds
  close_button_title: string
  save_host: boolean
  agent_installed: boolean
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
    install_msg: _t(
      'Run this command on your Windows host to download and install the Checkmk agent.'
    ),
    install_cmd: props.agent_install_cmds.windows,
    registration_msg: _t(
      'After you have downloaded the agent, run this command on your Windows host to register the Checkmk agent controller.'
    ),
    registration_cmd: props.agent_registration_cmds.windows.replace('[HOSTNAME]', props.host_name)
  },
  {
    id: 'linux',
    title: _t('Linux'),
    install_msg: _t(
      'Run this command on your Linux host to download and install the Checkmk agent.'
    ),
    install_deb_cmd: props.agent_install_cmds.linux_deb,
    install_rpm_cmd: props.agent_install_cmds.linux_rpm,
    install_tgz_cmd: props.agent_install_cmds.linux_tgz,
    install_url: props.legacy_agent_url
      ? {
          title: legacyInstallTitle,
          url: props.legacy_agent_url,
          msg: _t(
            'If you want to install the Checkmk agent on Linux, please read how to install the legacy agent'
          ),
          icon: 'learning-guide'
        }
      : undefined,
    registration_msg: _t(
      'After you have downloaded the agent, run this command on your Linux host to register the Checkmk agent controller.'
    ),
    registration_cmd: props.agent_registration_cmds.linux.replace('[HOSTNAME]', props.host_name),
    toggle_button_options: toggleButtonOptions
  },
  {
    id: 'solaris',
    title: _t('Solaris'),
    install_msg: _t('Run this command on your Solaris host to download the Checkmk agent.'),
    install_cmd: props.agent_install_cmds.solaris,
    install_url: props.legacy_agent_url
      ? {
          title: legacyInstallTitle,
          url: props.legacy_agent_url,
          msg: _t(
            'If you want to install the Checkmk agent on Solaris, please read how to install the legacy agent'
          ),
          icon: 'learning-guide'
        }
      : undefined,
    registration_msg: _t(
      'After you have downloaded the agent, run this command on your Solaris host to install the Checkmk agent.'
    ),
    registration_cmd: props.agent_registration_cmds.solaris.replace('[HOSTNAME]', props.host_name)
  },
  {
    id: 'aix',
    title: _t('AIX'),
    install_msg: _t('Run this command on your AIX host to download and install the Checkmk agent.'),
    install_cmd: props.agent_install_cmds.aix,
    install_url: props.legacy_agent_url
      ? {
          title: legacyInstallTitle,
          url: props.legacy_agent_url,
          msg: _t(
            'If you want to install the Checkmk agent on AIX, please read how to install the legacy agent'
          ),
          icon: 'learning-guide'
        }
      : undefined,
    registration_msg: _t(
      'After you have downloaded the agent, run this command on your AIX host to register the Checkmk agent controller.'
    ),
    registration_cmd: props.agent_registration_cmds.aix.replace('[HOSTNAME]', props.host_name)
  }
]
</script>

<template>
  <AgentSlideOut
    :dialog_msg="
      _t(
        `To monitor systems like Linux or Windows with Checkmk, you need to install an agent on these systems.
           This agent acts as a small program that collects data about the systems state, such as how much storage is used or the CPU load.`
      )
    "
    :tabs="tabs"
    :all_agents_url="all_agents_url"
    :close_button_title="close_button_title"
    :save_host="save_host"
    :agent_installed="agent_installed"
    :host_name="host_name"
    @close="close"
  />
</template>
