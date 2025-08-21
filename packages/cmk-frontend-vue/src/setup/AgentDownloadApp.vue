<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import AgentDownloadDialog from '@/setup/AgentDownloadDialog.vue'
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import usei18n from '@/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  output: string
  all_agents_url: string
  agent_slideout: AgentSlideout
}>()

const slideInTitle = ref(_t('Install Checkmk agent'))
const dialogTitle = ref(_t('Already installed the Checkmk agent?'))
const dialogMessage = ref(
  _t('This problem might be caused by a missing agent or the firewall settings.')
)
const slideInButtonTitle = ref(_t('Download & install agent'))

const notRegisteredSearchTerm = 'controller not registered'
const noTlsSearchTerm = 'is not providing it'
if (props.output.includes(notRegisteredSearchTerm)) {
  slideInTitle.value = _t('Register Checkmk agent')
  dialogTitle.value = _t('Already registered the Checkmk agent?')
  dialogMessage.value = _t('This problem might be caused by a missing agent registration.')
  slideInButtonTitle.value = _t('Register agent')
}

if (props.output.includes(noTlsSearchTerm)) {
  slideInTitle.value = _t('TLS connection not provided')
  dialogTitle.value = _t('Provide TLS connection')
  dialogMessage.value = _t(
    'The agent has been installed on the target system but is not providing a TLS connection.'
  )
  slideInButtonTitle.value = _t('Provide TLS connection')
}

const docsButtonTitle = _t('Read Checkmk user guide')
</script>

<template>
  <AgentDownloadDialog
    :dialog-title="dialogTitle"
    :dialog-message="dialogMessage"
    :slide-in-title="slideInTitle"
    :slide-in-button-title="slideInButtonTitle"
    :docs-button-title="docsButtonTitle"
    :close-button-title="_t('Close & run service discovery')"
    :agent-slideout="agent_slideout"
    :all-agents-url="all_agents_url"
    :is-not-registered="output.includes(notRegisteredSearchTerm)"
  />
</template>
