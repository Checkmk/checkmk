<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import { type AgentRegistrationCmds } from 'cmk-shared-typing/typescript/agent_slideout'
import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'
import type { AgentSlideOutTabs } from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

const props = defineProps<{
  all_agents_url: string
  host_name: string
  agent_registration_cmds: AgentRegistrationCmds
  close_button_title: string
  save_host: boolean
}>()

const { t } = usei18n('agent_install_slideout_content')
const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

const registrationMessage = t(
  'agent-windows-register-msg',
  'Run this command to register the Checkmk agent controller'
)

const tabs: AgentSlideOutTabs[] = [
  {
    id: 'windows',
    title: t('agent-windows', 'Windows'),
    registration_msg: registrationMessage,
    registration_cmd: props.agent_registration_cmds.windows.replace('[HOSTNAME]', props.host_name)
  },
  {
    id: 'linux',
    title: t('agent-linux', 'Linux'),
    registration_msg: registrationMessage,
    registration_cmd: props.agent_registration_cmds.linux.replace('[HOSTNAME]', props.host_name)
  },
  {
    id: 'solaris',
    title: t('agent-solaris', 'Solaris'),
    registration_msg: registrationMessage,
    registration_cmd: props.agent_registration_cmds.solaris.replace('[HOSTNAME]', props.host_name)
  },
  {
    id: 'aix',
    title: t('agent-solaris', 'AIX'),
    registration_msg: registrationMessage,
    registration_cmd: props.agent_registration_cmds.aix.replace('[HOSTNAME]', props.host_name)
  }
]
</script>

<template>
  <AgentSlideOut
    :dialog_msg="
      t(
        'ads-dialog-register-msg',
        'Agent registration configures TLS encryption to ensure secure communication, thereby guaranteeing that data transmitted between the agent and the server is secure and trustworthy.'
      )
    "
    :tabs="tabs"
    :all_agents_url="all_agents_url"
    :close_button_title="close_button_title"
    :save_host="save_host"
    @close="close"
  />
</template>
