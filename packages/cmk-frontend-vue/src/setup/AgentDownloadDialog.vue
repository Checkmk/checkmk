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

import CmkDialog from '@/components/CmkDialog.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

import AgentSlideOutContent from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'

interface Props {
  dialogTitle: TranslatedString
  dialogMessage: TranslatedString
  slideInTitle: TranslatedString
  slideInButtonTitle: TranslatedString
  docsButtonTitle: TranslatedString
  closeButtonTitle: TranslatedString
  agentSlideout: AgentSlideout
  isNotRegistered: boolean
  siteId: string
  siteServer: string
}

defineProps<Props>()

const slideInOpen = ref(false)

const openDocs = () => {
  window.open('https://docs.checkmk.com/latest/en/wato_monitoringagents.html#agents', '_blank')
}

const tooltipOpen = ref(true)
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
    <CmkTooltip :open="tooltipOpen" class="tooltip">
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
        <button class="tooltip-close" @click.prevent="tooltipOpen = false">×</button>
        <CmkDialog
          :title="dialogTitle"
          :message="dialogMessage"
          :buttons="[
            {
              title: slideInButtonTitle,
              onclick: () => {
                slideInOpen = true
              },
              variant: 'info'
            },
            {
              title: docsButtonTitle,
              onclick: () => {
                openDocs()
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
      @close="((slideInOpen = false), (tooltipOpen = false), triggerRescan())"
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
