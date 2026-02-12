<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type AgentSlideout } from 'cmk-shared-typing/typescript/agent_slideout'
import { TooltipArrow } from 'radix-vue'
import { ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkDialog from '@/components/CmkDialog.vue'
import CmkIcon from '@/components/CmkIcon'
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
  dialogCloseIconTitle: TranslatedString
  slideInTitle: TranslatedString
  slideInButtonTitle: TranslatedString
  hideButtonTitle: TranslatedString
  closeButtonTitle: TranslatedString
  agentSlideout: AgentSlideout
  isNotRegistered: boolean
  noTlsProvided: boolean
  siteId: string
  siteServer: string
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
        class="tooltip-content"
      >
        <TooltipArrow
          :style="{ fill: 'var(--default-help-icon-bg-color)' }"
          :width="6"
          :height="6"
        />
        <!-- eslint-disable-next-line vue/no-bare-strings-in-template -->
        <CmkIcon
          :title="dialogCloseIconTitle"
          class="tooltip-close"
          name="close"
          size="small"
          @click.stop="tooltipClosed = true"
        ></CmkIcon>
        <CmkDialog
          :title="dialogTitle"
          :message="dialogMessage"
          :buttons="[
            {
              title: slideInButtonTitle,
              onclick: () => {
                slideInOpen = true
              },
              variant: noTlsProvided || isNotRegistered ? 'info' : 'optional'
            },
            {
              title: hideButtonTitle,
              onclick: () => {
                tooltipHidden = true
              },
              variant: 'optional'
            }
          ]"
          class="setup-agent-download-dialog__dialog"
        />
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
      :agent-install-cmds="agentSlideout.agent_install_cmds"
      :agent-registration-cmds="agentSlideout.agent_registration_cmds"
      :legacy-agent-url="agentSlideout.legacy_agent_url"
      :close-button-title="closeButtonTitle"
      :save-host="agentSlideout.save_host"
      :host-exists="agentSlideout.host_exists ?? false"
      :setup-error="false"
      :agent-installed="isNotRegistered"
      :is-push-mode="false"
      @close="((slideInOpen = false), (tooltipHidden = true), triggerRescan())"
    />
  </CmkSlideInDialog>
</template>

<style scoped>
.setup-agent-download-dialog__dialog {
  margin: 20px 0 0 !important;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.tooltip-close {
  position: absolute;
  top: 22px;
  right: 4px;
  background: transparent;
  border: none;
  cursor: pointer;
  margin: 0;
  padding: 0;
}
</style>
