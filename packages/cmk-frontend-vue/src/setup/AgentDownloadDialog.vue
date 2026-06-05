<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import { TooltipArrow } from 'reka-ui'
import { ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

import AgentSlideOutContent from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'

interface Props {
  userId: string
  dialogTitle: TranslatedString
  dialogMessage: TranslatedString
  slideInTitle: TranslatedString
  slideInButtonTitle: TranslatedString
  hideButtonTitle: TranslatedString
  closeButtonTitle: TranslatedString
  agentSlideout: AgentSlideout
  isNotRegistered: boolean
  noTlsProvided: boolean
  isPushMode: boolean
  siteId: string
  siteServer: string
  agentReceiverPort: number
  agentReceiverPortIsDefault: boolean
}

const props = defineProps<Props>()

const slideInOpen = ref(false)

const localStorageKey = `service-discovery-${props.userId}-${props.agentSlideout.host_name}-hidden`
const tooltipHidden = usePersistentRef(localStorageKey, false, (v) => v as boolean)
const tooltipClosed = ref(false)

// The rescan button always contains the current js call with all needed
// params. Solution is not the best but without VUE on the setup page we have
// limited options to solve this.
const triggerRescan = () => {
  const rescanElement = [...document.querySelectorAll('a')].find(
    (a) => a.textContent.trim() === 'Rescan'
  ) as HTMLAnchorElement | null | undefined
  rescanElement?.click()
}
</script>

<template>
  <CmkTooltipProvider>
    <CmkTooltip :open="!tooltipHidden && !tooltipClosed" class="tooltip">
      <CmkTooltipTrigger as="span"></CmkTooltipTrigger>
      <CmkTooltipContent
        align="center"
        side="right"
        :avoid-collisions="false"
        :use-portal="true"
        class="setup-agent-download-dialog__tooltip-content"
      >
        <TooltipArrow
          :style="{ fill: 'var(--default-help-icon-bg-color)' }"
          :width="6"
          :height="6"
        />
        <CmkAlertBox
          :heading="dialogTitle"
          variant="info"
          :main-button="{
            title: slideInButtonTitle,
            onclick: () => {
              slideInOpen = true
            }
          }"
          :buttons="[
            {
              title: hideButtonTitle,
              onclick: () => {
                tooltipHidden = true
              },
              variant: 'optional'
            }
          ]"
          class="setup-agent-download-dialog__dialog"
        >
          {{ dialogMessage }}
        </CmkAlertBox>
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
  <CmkSlideInDialog
    :open="slideInOpen"
    :header="{ title: slideInTitle, closeButton: true }"
    @close="slideInOpen = false"
  >
    <AgentSlideOutContent
      :all-agents-url="agentSlideout.all_agents_url"
      :user-settings-url="agentSlideout.user_settings_url"
      :host-name="agentSlideout.host_name"
      :site-id="siteId"
      :site-server="siteServer"
      :agent-receiver-port="agentReceiverPort"
      :agent-receiver-port-is-default="agentReceiverPortIsDefault"
      :agent-install-cmds="agentSlideout.agent_install_cmds"
      :agent-registration-cmds="agentSlideout.agent_registration_cmds"
      :agent-status-cmds="agentSlideout.agent_status_cmds"
      :legacy-agent-url="agentSlideout.legacy_agent_url"
      :close-button-title="closeButtonTitle"
      :save-host="agentSlideout.save_host"
      :host-exists="agentSlideout.host_exists ?? false"
      :setup-error="false"
      :agent-installed="isNotRegistered"
      :is-push-mode="isPushMode"
      :unbaked-fallback="agentSlideout.unbaked_fallback ?? null"
      @close="((slideInOpen = false), (tooltipHidden = true), triggerRescan())"
    />
  </CmkSlideInDialog>
</template>

<style scoped>
.setup-agent-download-dialog__dialog {
  position: relative;
  top: 25px;
}
</style>

<style>
/* Unscoped, portal -> body */
.setup-agent-download-dialog__tooltip-content {
  z-index: var(--z-index-modal);
  max-width: var(--reka-tooltip-content-available-width);
}
</style>
