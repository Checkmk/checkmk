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
    title: t('agent_windows', 'Windows'),
    registration_msg: t(
      'agent_windows_register_msg',
      'Run this command to register the Checkmk agent controller'
    )
  },
  {
    id: 'linux',
    title: t('agent_linux', 'Linux'),
    registration_msg: t(
      'agent_windows_register_msg',
      'Run this command to register the Checkmk agent controller'
    )
  },
  {
    id: 'solaris',
    title: t('agent_solaris', 'Solaris'),
    registration_msg: t(
      'agent_windows_register_msg',
      'Run this command to register the Checkmk agent controller'
    )
  },
  {
    id: 'aix',
    title: t('agent_solaris', 'AIX'),
    registration_msg: t(
      'agent_windows_register_msg',
      'Run this command to register the Checkmk agent controller'
    )
  }
]
</script>

<template>
  <AgentSlideOut :url="url" :tabs="tabs" @close="close" />
</template>
