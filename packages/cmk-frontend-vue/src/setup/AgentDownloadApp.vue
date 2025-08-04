<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import AgentDownloadDialog from '@/setup/AgentDownloadDialog.vue'
import type { AgentDownloadI18N } from 'cmk-shared-typing/typescript/setup'
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'

defineProps<{
  all_agents_url: string
  host_name: string
  agent_slideout: AgentSlideout
  i18n: AgentDownloadI18N
}>()
</script>

<template>
  <AgentDownloadDialog
    :dialog_title="i18n.dialog_title"
    :dialog_message="i18n.dialog_message"
    :slide_in_title="i18n.slide_in_title"
    :slide_in_button_title="i18n.slide_in_button_title"
    :docs_button_title="i18n.docs_button_title"
    :host_name="host_name"
    :agent_slideout="agent_slideout"
    :all_agents_url="all_agents_url"
  />
</template>
