<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import AgentConnectionTest from '@/mode-host/agent-connection-test/AgentConnectionTest.vue'
import type { I18N } from 'cmk-shared-typing/typescript/agent_connection_test'
import { ref, onMounted } from 'vue'

defineProps<{
  url: string
  i18n: I18N
  input_hostname: string
  input_ipv4: string
  input_ipv6: string
}>()

const showTest = ref(true)

onMounted(() => {
  const formEditHost = document.getElementById('form_edit_host') as HTMLFormElement | null
  if (!formEditHost) {
    throw new Error(`Form with id "${'form_edit_host'}" not found`)
  }

  const changeTagAgent = document.getElementById(
    'cb_host_change_tag_agent'
  ) as HTMLInputElement | null
  const tagAgent = document.getElementById('tag_agent') as HTMLSelectElement | null
  formEditHost.addEventListener('change', (e: Event) => {
    switch (e.target) {
      case formEditHost || changeTagAgent:
        if (tagAgent) {
          showTest.value = tagAgent.value === 'all-agents' || tagAgent.value === 'cmk-agent'
        }
    }
  })
})
</script>

<template>
  <AgentConnectionTest
    v-if="showTest"
    :url="url"
    :dialog_message="i18n.dialog_message"
    :slide_in_title="i18n.slide_in_title"
    :msg_start="i18n.msg_start"
    :msg_success="i18n.msg_success"
    :msg_loading="i18n.msg_loading"
    :msg_missing="i18n.msg_missing"
    :msg_error="i18n.msg_error"
    :input_hostname="input_hostname"
    :input_ipv4="input_ipv4"
    :input_ipv6="input_ipv6"
  />
</template>
