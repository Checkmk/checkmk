<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import { type AgentDownloadServerPerSite } from 'cmk-shared-typing/typescript/setup'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import AgentDownloadDialog from '@/setup/AgentDownloadDialog.vue'

const { _t } = usei18n()

const props = defineProps<{
  user_id: string
  output: string
  site: string
  server_per_site: Array<AgentDownloadServerPerSite>
  agent_slideout: AgentSlideout
}>()

const slideInTitle = ref(_t('Install Checkmk agent'))
const dialogTitle = ref(_t('Agent communication failed during service discovery'))
const dialogMessage = ref(
  _t(`This can have different reasons. The Checkmk agent might not be installed, or communication may be blocked by firewall or network settings.
If this host should be monitored via an agent, check the installation and connectivity.
If not, you can ignore this message.`)
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

const hideButtonTitle = _t('Ignore for this host')
const siteServer = props.server_per_site.find((item) => item.site_id === props.site)?.server ?? ''
</script>

<template>
  <AgentDownloadDialog
    :user-id="props.user_id"
    :dialog-title="dialogTitle"
    :dialog-message="dialogMessage"
    :dialog-close-icon-title="_t('Close for now')"
    :slide-in-title="slideInTitle"
    :slide-in-button-title="slideInButtonTitle"
    :hide-button-title="hideButtonTitle"
    :close-button-title="_t('Close & run service discovery')"
    :agent-slideout="agent_slideout"
    :is-not-registered="output.includes(notRegisteredSearchTerm)"
    :no-tls-provided="props.output.includes(noTlsSearchTerm)"
    :site-id="site"
    :site-server="siteServer"
  />
</template>
