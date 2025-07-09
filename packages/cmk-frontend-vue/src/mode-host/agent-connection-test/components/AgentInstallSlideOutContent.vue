<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

defineProps<{
  url: string
}>()

const { t } = usei18n('agent_install_slideout_content')
const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

export interface AgentInstallTabs {
  id: string
  title: string
  install_msg: string
  registration_msg: string
}

const tabs: AgentInstallTabs[] = [
  {
    id: 'windows',
    title: t('agent_windows', 'Windows'),
    install_msg: t(
      'agent_windows_install_msg',
      'Run this command on your Windows host to download and install the Checkmk agent.'
    ),
    registration_msg: t(
      'agent_windows_registration_msg',
      'After you have downloaded the agent, run this command on your Windows host to register the Checkmk agent controller.'
    )
  },
  {
    id: 'linux',
    title: t('agent_linux', 'Linux'),
    install_msg: t(
      'agent_linux_install_msg',
      'Run this command on your Linux host to download and install the Checkmk agent.'
    ),
    registration_msg: t(
      'agent_linux_registration_msg',
      'After you have downloaded the agent, run this command on your Linux host to register the Checkmk agent controller.'
    )
  },
  {
    id: 'solaris',
    title: t('agent_solaris', 'Solaris'),
    install_msg: t(
      'agent_solaris_install_msg',
      'Run this command on your Solaris host to download the Checkmk agent.'
    ),
    registration_msg: t(
      'agent_solaris_registration_msg',
      'After you have downloaded the agent, run this command on your Solaris host to install the Checkmk agent.'
    )
  },
  {
    id: 'aix',
    title: t('agent_solaris', 'AIX'),
    install_msg: t(
      'agent_aix_install_msg',
      'Run this command on your AIX host to download and install the Checkmk agent.'
    ),
    registration_msg: t(
      'agent_aix_registration_msg',
      'After you have downloaded the agent, run this command on your AIX host to register the Checkmk agent controller.'
    )
  }
]
</script>

<template>
  <AgentSlideOut :url="url" :tabs="tabs" @close="close" />
</template>
