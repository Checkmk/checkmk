<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'
import type { AgentSlideOutTabs } from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

defineProps<{
  url: string
}>()

const { t } = usei18n('agent_install_slideout_content')
const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

const tabs: AgentSlideOutTabs[] = [
  {
    id: 'windows',
    title: t('agent-windows', 'Windows'),
    install_msg: t(
      'agent_windows_install_msg',
      'Run this command on your Windows host to download and install the Checkmk agent.'
    ),
    registration_msg: t(
      'agent-windows-registration-msg',
      'After you have downloaded the agent, run this command on your Windows host to register the Checkmk agent controller.'
    )
  },
  {
    id: 'linux',
    title: t('agent-linux', 'Linux'),
    install_msg: t(
      'agent-linux-install-msg',
      'Run this command on your Linux host to download and install the Checkmk agent.'
    ),
    registration_msg: t(
      'agent-linux-registration-msg',
      'After you have downloaded the agent, run this command on your Linux host to register the Checkmk agent controller.'
    )
  },
  {
    id: 'solaris',
    title: t('agent_solaris', 'Solaris'),
    install_msg: t(
      'agent-solaris-install-msg',
      'Run this command on your Solaris host to download the Checkmk agent.'
    ),
    registration_msg: t(
      'agent-solaris-registration-msg',
      'After you have downloaded the agent, run this command on your Solaris host to install the Checkmk agent.'
    )
  },
  {
    id: 'aix',
    title: t('agent_solaris', 'AIX'),
    install_msg: t(
      'agent-aix-install-msg',
      'Run this command on your AIX host to download and install the Checkmk agent.'
    ),
    registration_msg: t(
      'agent-aix-registration-msg',
      'After you have downloaded the agent, run this command on your AIX host to register the Checkmk agent controller.'
    )
  }
]
</script>

<template>
  <AgentSlideOut
    :dialog_msg="
      t(
        'ads-dialog-install-msg',
        'To monitor systems like Linux or Windows with Checkmk, you need to install an agent on these systems. This agent acts as a small program that collects data about the systems state, such as how much storage is used or the CPU load'
      )
    "
    :tabs="tabs"
    :url="url"
    @close="close"
  />
</template>
