<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type AgentInstallCmds,
  type AgentRegistrationCmds,
  type AgentStatusCmds,
  type UnbakedFallback
} from 'cmk-shared-typing/typescript/agent_slideout'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import AgentSlideOut from '@/mode-host/agent-connection-test/components/AgentSlideOut.vue'

import type { HostMacros } from '../lib/commandTemplate'
import { buildFlavours } from '../lib/flavours'

const props = defineProps<{
  allAgentsUrl: string
  userSettingsUrl: string
  legacyAgentUrl: string | undefined
  hostName: string
  siteId: string
  siteServer: string
  agentReceiverPort: number
  agentReceiverPortIsDefault: boolean
  agentInstallCmds: AgentInstallCmds
  agentRegistrationCmds: AgentRegistrationCmds
  agentStatusCmds: AgentStatusCmds
  closeButtonTitle: TranslatedString
  saveHost: boolean
  hostExists: boolean
  setupError: boolean
  agentInstalled: boolean
  isPushMode: boolean
  unbakedFallback: UnbakedFallback | null
}>()

const { _t } = usei18n()

const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

/** The agent receiver is reached at the site host, on its own port. */
function registrationServer(): string {
  let host: string
  if (props.siteServer) {
    try {
      host = new URL(props.siteServer).hostname
    } catch {
      host = props.siteServer
    }
  } else {
    host = window.location.hostname
  }
  return `${host}:${props.agentReceiverPort}`
}

const macros = computed<HostMacros>(() => ({
  hostName: props.hostName,
  siteId: props.siteId,
  downloadServer: props.siteServer || `${window.location.protocol}//${window.location.host}`,
  registrationServer: registrationServer()
}))

const flavours = computed(() =>
  buildFlavours({
    installCmds: props.agentInstallCmds,
    registrationCmds: props.agentRegistrationCmds,
    statusCmds: props.agentStatusCmds,
    legacyAgentUrl: props.legacyAgentUrl,
    unbakedFallback: props.unbakedFallback
  })
)
</script>

<template>
  <AgentSlideOut
    :dialog-msg="
      _t(
        `To monitor systems like Linux or Windows with Checkmk, you need to install an agent on these systems.
           This agent acts as a small program that collects data about the systems state, such as how much storage is used or the CPU load.`
      )
    "
    :flavours="flavours"
    :macros="macros"
    :all-agents-url="allAgentsUrl"
    :user-settings-url="userSettingsUrl"
    :close-button-title="closeButtonTitle"
    :save-host="saveHost"
    :host-exists="hostExists"
    :setup-error="setupError"
    :agent-installed="agentInstalled"
    :host-name="hostName"
    :site-id="siteId"
    :is-push-mode="isPushMode"
    :agent-receiver-port-is-default="agentReceiverPortIsDefault"
    @close="close"
  />
</template>
